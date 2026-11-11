# EasyMeasurement - tests/test_report_structure.py
# Reports by the structure of the installation: blocks that state what they share, the
# figures that count, remarks and photos as footnotes.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timedelta

import pytest
from PIL import Image

from easymeasurement.campaign.photo_marks import PhotoMark
from easymeasurement.model import MeterMeasurement, Quantity, ResultValue, Verdict
from easymeasurement.reporting.context import ReportMeasurement, ReportStep, build_context
from easymeasurement.reporting.footnotes import Footnotes
from easymeasurement.reporting.measurement_table import group_nodes
from easymeasurement.reporting.nodes import Fields, Heading, Table, plain
from easymeasurement.reporting.pdf import render_pdf
from easymeasurement.reporting.template import resolve

T0 = datetime(2026, 3, 1, 10, 0)


def rlo(value="0.21Ω", offset="0.04Ω", verdict=Verdict.PASSED, n=0, settings=None):
    results = (
        ResultValue("rlo", "RLO", Quantity.parse(value), verdict, "", "<1.00Ω"),
        ResultValue("rlo_plus", "RLO+", Quantity.parse(value), verdict, "", "<1.00Ω"),
        ResultValue("rlo_minus", "RLO-", Quantity.parse("0.19Ω"), verdict, "", "<1.00Ω"),
        ResultValue("rlo_offset", "RLO-OFFSET", Quantity.parse(offset)),
    )
    data = MeterMeasurement(f"m{n}", "rlo", T0, verdict, results=results)
    shared = [("Polarität", "Automatisch"), ("Messdauer", "AUTO")]
    return ReportMeasurement(data, T0 + timedelta(minutes=n), settings=settings or shared)


def table_and_head(group):
    nodes = group_nodes(group, {"summary": True}, Footnotes())
    head = nodes[0].rows if isinstance(nodes[0], Fields) else []
    return dict(head), nodes[-1].body


def test_a_passed_rlo_shows_neither_polarity():
    head, table = table_and_head([rlo(n=1), rlo("0.30Ω", n=2)])
    assert [plain(h) for h in table.headers] == ["Nr.", "Zeitpunkt", "RLO", "Bewertung", "Bemerkung"]
    assert head["Bedingungen"] == "<i>R</i><sub rise='30%'>LO,Offset</sub> = 40 mΩ"
    assert head["Grenzwerte"] == "<i>R</i><sub rise='30%'>LO</sub> &lt; 1,00 Ω"


def test_the_polarities_appear_once_a_measurement_did_not_pass():
    _, table = table_and_head([rlo(n=1), rlo("1.20Ω", verdict=Verdict.FAILED, n=2)])
    assert [plain(h) for h in table.headers][2:5] == ["RLO", "RLO+", "RLO−"]
    assert table.rows[0][3] == "–" and table.rows[1][3] == "1,20 Ω"


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
    remarks = [row[-1] for row in node.body.rows]
    assert remarks == ["siehe Hinweis 1 in [1]", "Lack entfernt\nsiehe [2], [3]"]
    assert node.refs == [[0], [1, 2]]
    assert node.photos[0].notes == ["1  Klemme"]


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
        "Schrank / Tür (Messpunkt)", "RLO – Schutzleiterwiderstand",
    ]


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


def photo(path):
    Image.new("RGB", (400, 300), "steelblue").save(path, "JPEG")
    return path


@pytest.mark.skipif(shutil.which("pdfimages") is None, reason="needs pdfimages")
def test_no_page_holds_more_than_two_rows_of_photos(tmp_path):
    group = []
    for n in range(9):
        measurement = rlo(n=n)
        measurement.photos.append(photo(tmp_path / f"{n}.jpg"))
        group.append(measurement)
    lonely = rlo(n=20)
    lonely.photos += [photo(tmp_path / f"x{n}.jpg") for n in range(8)]
    buffer = io.BytesIO()
    render_pdf(group_nodes(group, {}, Footnotes()) + group_nodes([lonely], {}, Footnotes()),
               buffer)
    target = tmp_path / "report.pdf"
    target.write_bytes(buffer.getvalue())
    listing = subprocess.run(["pdfimages", "-list", str(target)], capture_output=True,
                             text=True, timeout=60, check=True).stdout.splitlines()[2:]
    per_page = Counter(line.split()[0] for line in listing)
    assert sum(per_page.values()) == 17
    assert max(per_page.values()) <= 6


def test_a_photo_a_measurement_shows_is_not_shown_again(tmp_path):
    measurement = rlo()
    measurement.photos.append(tmp_path / "a.jpg")
    block = {"type": "steps", "blocks": [{"type": "measurements"}, {"type": "photos"}]}
    step = ReportStep("Schutzleiter", "rlo", "done", "", [measurement])
    (node,) = resolve({"blocks": [block]}, {"campaign": {}, "steps": [step]})
    assert [note.number for note in node.photos] == [1]
    assert ("Bemerkung", "siehe [1]") in node.body.rows


def test_place_date_and_name_are_written_on_the_signature_lines():
    from easymeasurement.reporting.template_model import FILLED_PLACE

    block = {"type": "signature", "labels": ["Ort, Datum", "Unterschrift"],
             "fills": [FILLED_PLACE, "{{ campaign.tester }}"]}
    values = {"campaign": {"tester": "Max Prüfer"}, "steps": [], "company": {"city": "Musterstadt"},
              "report": {"date": "01.03.2026"}}
    (node,) = resolve({"blocks": [block]}, values)
    assert node.fills == ["Musterstadt, 01.03.2026", "Max Prüfer"]
    values["company"]["city"] = ""
    assert resolve({"blocks": [block]}, values)[0].fills[0] == "01.03.2026"
    buffer = io.BytesIO()
    render_pdf([node], buffer)
    assert buffer.getvalue().startswith(b"%PDF")


def test_measurement_block_outside_a_repeat_covers_the_campaign():
    template = {"blocks": [{"type": "measurements"}]}
    step = ReportStep("Schutzleiter", "rlo", "done", "", [rlo(n=1), rlo(n=2)])
    values = {"campaign": {}, "steps": [step]}
    head, node = resolve(template, values)
    assert isinstance(node.body, Table) and len(node.body.rows) == 2


def test_the_remarks_take_the_room_the_other_columns_leave():
    from easymeasurement.reporting.pdf_tables import column_widths

    headers = ["Nr.", "Zeit", "Bemerkung"]
    rows = [["1", "10:00:00", "kurz"]]
    widths = column_widths(headers, rows, [], 400, ("Helvetica", "Helvetica-Bold"), 8.5, 2)
    assert sum(widths) == pytest.approx(400) and widths[2] > 300
    even = column_widths(headers, rows, [], 400, ("Helvetica", "Helvetica-Bold"), 8.5)
    assert even[2] < 300


def test_the_letterhead_names_the_later_pages():
    from easymeasurement.reporting.nodes import Letterhead
    from easymeasurement.reporting.pdf_pages import running_head

    head = Letterhead("Prüfprotokoll", ["Prüfung", "Maschine: Presse", "Prüfung vom 01.03.2026"],
                      [], [])
    assert running_head([head]) == ("Prüfprotokoll · Prüfung · Maschine: Presse",
                                    "Prüfung vom 01.03.2026")
    assert running_head([]) == ("", "")


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
