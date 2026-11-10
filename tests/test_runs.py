# EasyMeasurement - tests/test_runs.py
# Runs: steps measured as one named sequence, folded into one line of the table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from datetime import datetime

import pytest
from PySide6.QtCore import Qt

from easymeasurement.campaign.seal import content
from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.ui.common import RUN_ID, selected_ids

FUNCTION, VALUES = 5, 6
QUESTIONS = (("Zugänglichkeit", "Ist die Anlage zugänglich?", "yes"),
             ("Schaltpläne", "Stimmen die Schaltpläne?", "no"),
             ("Warnhinweise", "Sind Warnhinweise angebracht?", "yes"))


@pytest.fixture
def shown(window, app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    campaign = app.service.create(press, "Prüfung", "Prüfer")
    moment = datetime(2026, 5, 4, 9)
    run = app.service.add_run(campaign, "Sichtprüfung der Betriebsmittel", "Sichtprüfung", moment)
    for name, question, answer in QUESTIONS:
        values = [ResultValue("question", "Prüffrage", Quantity(raw=question)),
                  ResultValue("answer", "Antwort", Quantity(raw=answer))]
        verdict = Verdict.PASSED if answer == "yes" else Verdict.FAILED
        step = app.service.add_measurement(campaign, "visual_inspection", values, moment,
                                           verdict, asset_id=cabinet)
        app.service.join_run(step, run, name)
    riso = ResultValue("riso", "RISO", Quantity.parse("20MΩ"), Verdict.PASSED, ">1MΩ", "")
    app.service.add_measurement(campaign, "riso", [riso], datetime(2026, 5, 4, 10),
                                Verdict.PASSED, asset_id=cabinet)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return {"page": page, "values": page.values, "run": run, "campaign": campaign,
            "press": press, "cabinet": cabinet}


def _texts(values, column):
    return [values.table.item(row, column).text() for row in range(values.table.rowCount())]


def test_a_run_is_one_line_until_it_is_opened(shown):
    values = shown["values"]
    assert values.table.rowCount() == 2
    head = values.table.item(0, 0)
    assert head.data(RUN_ID) == shown["run"]
    assert _texts(values, VALUES)[0] == (
        "Sichtprüfung der Betriebsmittel  ·  3 Schritte  ·  1 Mangel")
    assert _texts(values, FUNCTION)[0] == "Sichtprüfung"
    values._clicked(0, 0, False)
    assert _texts(values, FUNCTION)[1:4] == ["Zugänglichkeit", "Schaltpläne", "Warnhinweise"]
    assert values.table.item(2, VALUES).text() == "nein – Stimmen die Schaltpläne?"


def test_steps_stay_under_their_head_whatever_sorts(shown):
    values = shown["values"]
    values.toggle_run(shown["run"])
    header = values.table.horizontalHeader()
    for column in (VALUES, FUNCTION, 8):
        for order in (Qt.SortOrder.AscendingOrder, Qt.SortOrder.DescendingOrder):
            header.setSortIndicator(column, order)
            names = _texts(values, FUNCTION)
            start = names.index("Sichtprüfung")
            assert names[start + 1:start + 4] == ["Zugänglichkeit", "Schaltpläne",
                                                  "Warnhinweise"]


def test_the_line_of_a_run_moves_all_its_steps(shown, app):
    values = shown["values"]
    values.table.selectRow(0)
    ids = selected_ids(values.table)
    assert len(ids) == 3
    app.service.move_measurements(ids, shown["press"])
    rows = app.db.query("SELECT asset_id FROM measurements WHERE run_id=?", shown["run"])
    assert {row["asset_id"] for row in rows} == {shown["press"]}


def test_a_defect_inside_a_folded_run_opens_it(shown, app):
    page = shown["page"]
    page._follow_check("failed")
    row = page.values.table.currentRow()
    assert page.values.table.item(row, FUNCTION).text() == "Schaltpläne"


def test_the_seal_counts_a_run_only_where_there_is_one(shown, app):
    record = json.loads(content(app.db, shown["campaign"], "2026-05-04T12:00:00"))
    steps = [m for m in record["measurements"] if "run" in m]
    assert len(steps) == 3 and steps[0]["run"]["name"] == "Sichtprüfung der Betriebsmittel"
    single = [m for m in record["measurements"] if "run" not in m]
    assert "step_name" not in single[0] and "run_id" not in single[0]["measurement"]


def test_the_measurement_names_its_element_instead_of_a_long_path(shown):
    values = shown["values"]
    values.table.selectRow(1)
    editor = values.editor
    assert editor.place.isVisibleTo(editor) and not editor.location.isVisibleTo(editor)
    assert "Schrank" in editor.place.name.text()
    assert editor.place.way.full == "Presse"
    assert editor.place.button.isVisibleTo(editor)


def test_properties_are_stored_only_on_taking_them_over(shown, app):
    from easymeasurement.ui.element_form import ElementOverlay
    overlay = ElementOverlay(app, shown["cabinet"])
    assert (overlay.ok_button.text(), overlay.cancel_button.text()) == ("Übernehmen", "Abbrechen")
    overlay.form.fields["name"].setText("Schrank X1")
    overlay.form.fields["name"].editingFinished.emit()
    assert app.db.asset(shown["cabinet"])["name"] == "Schrank"  # not yet
    overlay.accept()
    assert app.db.asset(shown["cabinet"])["name"] == "Schrank X1"
