# OkeyDocu - tests/test_report_structure.py
# Reports by the structure of the installation: blocks that state what they share, the
# figures that count, remarks and photos as footnotes.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import timedelta

import pytest

from okeydocu.campaign.photo_marks import PhotoMark
from okeydocu.model import MeterMeasurement, Quantity, ResultValue, Verdict
from okeydocu.reporting.context import (
    ReportMeasurement,
    ReportStep,
    build_context,
)
from okeydocu.reporting.footnotes import Footnotes
from okeydocu.reporting.language import speaking
from okeydocu.reporting.measurement_table import group_nodes
from okeydocu.reporting.nodes import Fields, Heading, plain
from okeydocu.reporting.template import resolve

from .rlo_helpers import T0, rlo


def table_and_head(group):
    nodes = group_nodes(group, {"summary": True}, Footnotes())
    head = nodes[0].rows if isinstance(nodes[0], Fields) else []
    return dict(head), nodes[-1].body


def test_equal_directions_show_rlo_alone():
    head, table = table_and_head([rlo(n=1), rlo("0.30Ω", n=2)])
    assert [plain(h) for h in table.headers] == ["Nr.", "Zeitpunkt", "RLO", "", "Bemerkung"]
    assert head["Bedingungen"] == "<i>R</i><sub rise='30%'>LO,Offset</sub> = 40 mΩ"
    assert head["Grenzwerte"] == "<i>R</i><sub rise='30%'>LO</sub> &lt; 1,00 Ω"


def test_directions_that_differ_show_the_higher_in_place_of_rlo():
    group = [rlo(n=1), rlo("0.43Ω", n=2, directions=("0.34Ω", "0.43Ω"))]
    head, table = table_and_head(group)
    assert [plain(h) for h in table.headers][2:4] == ["RLO", ""]
    assert plain(table.rows[0][2]) == "210 mΩ"
    assert plain(table.rows[1][2]) == "430 mΩ (RLO−)"
    assert plain(table.rows[1][-1]) == "RLO+ = 340 mΩ"
    assert head["Grenzwerte"] == "<i>R</i><sub rise='30%'>LO</sub> &lt; 1,00 Ω"


def test_what_differs_gets_a_column_and_what_is_shared_stands_above():
    other = [("Polarität", "+Pol an PE"), ("Messdauer", "AUTO")]
    head, table = table_and_head([rlo(n=1), rlo(offset="0.05Ω", n=2, settings=other)])
    assert head["Einstellungen"] == "Messdauer: AUTO"
    assert "Polarität" in table.headers
    assert "RLO,Offset" in [plain(h) for h in table.headers]


def test_a_remark_names_the_notes_in_its_photo(tmp_path):
    first, second = rlo(n=1), rlo(n=2)
    first.photos.append(tmp_path / "a.jpg")
    first.photo_notes[str(tmp_path / "a.jpg")] = ("hint", [PhotoMark(1, .1, .1, .2, .2, "Klemme")])
    second.photos += [tmp_path / "b.jpg", tmp_path / "c.jpg"]
    second.data = MeterMeasurement("m2", "rlo", T0, Verdict.PASSED, comment="Lack entfernt",
                                   results=second.data.results)
    node = group_nodes([first, second], {}, Footnotes())[-1]
    remarks = [plain(row[-1]) for row in node.body.rows]
    assert remarks == ["siehe Hinweis 1 in [1]", "Lack entfernt\nsiehe [2], [3]"]
    assert node.refs == [[0], [1, 2]]
    assert node.photos[0].notes == ["1  Klemme"]


def test_the_hint_stands_beneath_the_photos_marked_as_a_notice(tmp_path):
    measured = rlo(n=1)
    measured.hint = "Abdeckung links\nSchlüssel beim Hausmeister"
    for name, role in (("a.jpg", "hint"), ("b.jpg", "")):
        measured.photos.append(tmp_path / name)
        measured.photo_notes[str(tmp_path / name)] = (role, [PhotoMark(1, .1, .1, .2, .2, "PE")])
    notice, plain_photo = group_nodes([measured], {}, Footnotes())[-1].photos
    assert notice.notes == ["Abdeckung links", "Schlüssel beim Hausmeister", "1  PE"]
    assert plain_photo.notes == ["1  PE"]


@pytest.fixture
def tree(app):
    db = app.db
    customer = db.add_customer("Muster AG")
    root = db.add_asset(customer, "machine", "Presse")
    board = db.add_asset(customer, "distribution_board", "Schrank", parent_id=root)
    point = db.add_asset(customer, "measuring_point", "Tür", parent_id=board)
    campaign = app.service.create(root, "Prüfung", "Prüfer")
    for asset, value in ((root, "0.10Ω"), (point, "0.20Ω"), (point, "0.30Ω"), (board, "0.40Ω")):
        result = ResultValue("rlo", "RLO", Quantity.parse(value), Verdict.PASSED, "", "<1.00Ω")
        app.service.add_measurement(campaign, "rlo", [result], T0, Verdict.PASSED,
                                    asset_id=asset)
    return campaign


def headings(nodes):
    return [plain(node.text) for node in nodes if isinstance(node, Heading)]


def test_levels_follow_the_structure_tree(app, tree):
    nodes = resolve({"blocks": [{"type": "structure"}]}, build_context(app.service, tree))
    assert headings(nodes) == [
        "Presse (Maschine)", "RLO – Schutzleiterwiderstand",
        "Schrank (Verteiler)", "RLO – Schutzleiterwiderstand",
        "Schrank\u202f/\u2009Tür (Messpunkt)", "RLO – Schutzleiterwiderstand",
    ]


def test_the_report_takes_the_hint_of_each_measurement(app, tree):
    app.db.execute("UPDATE measurements SET hint='hinter der Tür'")
    measured = [m for step in build_context(app.service, tree)["steps"] for m in step.measurements]
    assert {m.hint for m in measured} == {"hinter der Tür"}


def test_by_function_the_shared_limit_is_said_once(app, tree):
    block = {"type": "structure", "order": "function"}
    nodes = resolve({"blocks": [block]}, build_context(app.service, tree))
    assert headings(nodes)[:2] == ["RLO – Schutzleiterwiderstand", "Presse (Maschine)"]
    heads = [node for node in nodes if isinstance(node, Fields)]
    assert [list(dict(head.rows)) for head in heads] == [["Grenzwerte"]]


def test_steps_without_measurement_are_listed_with_their_reason():
    step = ReportStep("Schutzleiter Motor", "rlo", "skipped", "kein Zugang", [])
    values = {"campaign": {}, "steps": [step], "asset": {"name": "Presse"}}
    nodes = resolve({"blocks": [{"type": "structure"}]}, values)
    assert headings(nodes) == ["Nicht gemessen"]
    assert nodes[-1].rows == [("Schutzleiter Motor", "kein Zugang")]


def test_elements_side_by_side_follow_the_order_they_were_measured_in(app):
    db = app.db
    customer = db.add_customer("Muster AG")
    root = db.add_asset(customer, "machine", "Presse")
    early, late = (db.add_asset(customer, "measuring_point", name, parent_id=root)
                   for name in ("Zuleitung", "Antrieb"))
    campaign = app.service.create(root, "Prüfung", "Prüfer")
    for asset, minute in ((late, 30), (early, 10), (late, 5)):
        result = ResultValue("rlo", "RLO", Quantity.parse("0.10Ω"), Verdict.PASSED, "", "<1.00Ω")
        app.service.add_measurement(campaign, "rlo", [result], T0 + timedelta(minutes=minute),
                                    Verdict.PASSED, asset_id=asset)
    nodes = resolve({"blocks": [{"type": "structure"}]}, build_context(app.service, campaign))
    places = [title for title in headings(nodes) if "Messpunkt" in title]
    assert places == ["Antrieb (Messpunkt)", "Zuleitung (Messpunkt)"]
    times = [row[1][:8] for node in nodes if hasattr(node, "body") for row in node.body.rows]
    assert times == ["10:05:00", "10:30:00", "10:10:00"]


def test_an_element_says_what_it_is_and_how_it_was_measured(app):
    db = app.db
    customer = db.add_customer("Muster AG")
    root = db.add_asset(customer, "machine", "Presse", identifier="M-1", manufacturer="Muster",
                        comment="Messungen von links nach rechts")
    campaign = app.service.create(root, "Prüfung", "Prüfer")
    result = ResultValue("rlo", "RLO", Quantity.parse("0.10Ω"), Verdict.PASSED, "", "<1.00Ω")
    app.service.add_measurement(campaign, "rlo", [result], T0, Verdict.PASSED, asset_id=root)
    nodes = resolve({"blocks": [{"type": "structure"}]}, build_context(app.service, campaign))
    card = next(node for node in nodes if isinstance(node, Fields))
    assert card.rows == [("Kennung", "M-1"), ("Hersteller", "Muster"),
                         ("Bemerkung", "Messungen von links nach rechts")]


def test_compact_puts_every_function_of_an_element_into_one_table():
    from okeydocu.reporting.compact import compact_nodes

    three_phase = ReportMeasurement(MeterMeasurement("u3", "u3", T0, Verdict.PASSED, results=(
        ResultValue("u_l1l2", "UL1L2", Quantity.parse("400V")),
        ResultValue("u_l2l3", "UL2L3", Quantity.parse("401V")))), T0 + timedelta(minutes=9))
    head, node = compact_nodes([rlo(n=1), rlo(offset="0.05Ω", n=2), three_phase], Footnotes())
    table = node.body
    assert [plain(h) for h in table.headers] == ["Nr.", "Zeitpunkt", "Messung", "Ergebnis",
                                                 "Grenzwert", "", "Bemerkung"]
    assert plain(compact_nodes([rlo(n=3)], Footnotes())[-1].body.rows[0][2]) == "RLO"
    assert [plain(row[2]) for row in table.rows] == ["RLO", "RLO", "U3~"]
    assert plain(table.rows[0][4]) == "<\u202f1,00\u202fΩ"
    assert "<br/>" in table.rows[2][3]
    assert "= 40 mΩ" in table.rows[0][-1] and "= 50 mΩ" in table.rows[1][-1]
    assert [plain(label) for label, _ in head.rows] == ["RLO"]


def test_a_time_all_rows_share_is_said_once_above():
    group = [rlo(n=1), rlo(n=2)]
    for measurement in group:
        measurement.local_time = T0
    head, table = table_and_head(group)
    assert head["Zeitpunkt"] == "01.03.2026 10:00:00" and "Zeitpunkt" not in table.headers


def test_a_figure_few_rows_have_joins_their_remark():
    group = [rlo(n=1), rlo(n=2), rlo(n=3)]
    group[2].data = MeterMeasurement("m3", "rlo", T0, Verdict.PASSED, results=(
        *group[2].data.results, ResultValue("rlo_delta", "dRLO", Quantity.parse("0.09Ω"))))
    _, table = table_and_head(group)
    assert [plain(h) for h in table.headers] == ["Nr.", "Zeitpunkt", "RLO", "", "Bemerkung"]
    assert plain(table.rows[2][-1]) == "ΔRLO = 90 mΩ"


def test_a_setting_is_named_without_the_group_the_instrument_puts_before_it():
    from okeydocu.reporting.measurement_words import _without_group

    named = [("RCD - Typ", "B"), ("RCD - Nennstrom", "63 A"), ("RISO/RLO Messdauer", "AUTO")]
    assert _without_group(named) == [("Typ", "B"), ("Nennstrom", "63 A"),
                                     ("RISO/RLO Messdauer", "AUTO")]
    twice = [("RCD - Typ", "B"), ("Netz - Typ", "TN"), ("RCD - Faktor", "1x")]
    assert _without_group(twice) == [("RCD-Typ", "B"), ("Netz-Typ", "TN"), ("Faktor", "1x")]


def test_a_setting_writes_its_numbers_as_the_language_does():
    from okeydocu.reporting.measurement_words import in_decimals

    with speaking("de"):
        assert in_decimals("gL/gG <0.2s") == "gL/gG <0,2s"
        assert in_decimals("1.0x IΔN") == "1,0x IΔN"
        assert in_decimals("13.02.2023") == "13.02.2023"
    with speaking("en"):
        assert in_decimals("1.0x IΔN") == "1.0x IΔN"


def test_a_lower_and_an_upper_limit_read_as_a_range():
    from okeydocu.reporting.measurement_table import limit_markup

    assert limit_markup("t", "> 0 ms < 300 ms") == "0 ms &lt; t &lt; 300 ms"
    assert limit_markup("R", "< 1,00 Ω") == "R &lt; 1,00 Ω"


def test_photos_of_an_element_that_say_the_same_share_a_row():
    from okeydocu.reporting.summary import _merged, numbers_text

    assert numbers_text([3]) == "[3]"
    assert numbers_text([3, 4]) == "[3], [4]"
    assert numbers_text([3, 4, 5, 9]) == "[3]–[5], [9]"
    rows = [("Schrank", 1, "lösen"), ("Schrank", 2, "lösen"), ("Schrank", 3, "lösen"),
            ("Schrank", 4, "anders"), ("Tür", 5, "anders")]
    assert _merged(rows) == [["Schrank", "[1]–[3]", "lösen"], ["Schrank", "[4]", "anders"],
                             ["Tür", "[5]", "anders"]]
