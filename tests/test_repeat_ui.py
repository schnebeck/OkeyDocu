# OkeyDocu - tests/test_repeat_ui.py
# A repeat inspection on screen: the open points in the table and beside it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.model import MeterMeasurement, Parameter, Quantity, ResultValue, Verdict
from okeydocu.ui.campaign_dialog import CampaignDialog
from okeydocu.ui.common import POINT_ID
from okeydocu.ui.guided_pages import ReasonOverlay

VALUES = 6


def _riso(uid, text="20MΩ"):
    value = ResultValue("riso", "RISO", Quantity.parse(text), Verdict.PASSED, ">1.00MΩ", "")
    return MeterMeasurement(uid=uid, function="riso", taken_at=datetime(2026, 5, 4, 9),
                            verdict=Verdict.PASSED, results=(value,),
                            parameters=(Parameter("RISO - Nennspannung", "500 V"),))


@pytest.fixture
def repeat(window, app, monkeypatch):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    first = app.service.create(press, "Erstprüfung", "Prüfer")
    app.service.insert_imported(first, _riso("old"), "import:test", datetime(2025, 5, 4, 9),
                                None, None, None, cabinet)
    values = [ResultValue("question", "Prüffrage", Quantity(raw="Ist der Schrank zu?")),
              ResultValue("answer", "Antwort", Quantity(raw="yes"))]
    app.service.add_measurement(first, "visual_inspection", values, datetime(2025, 5, 4, 8),
                                Verdict.PASSED, asset_id=cabinet)
    app.service.close(first)
    app.db.add_user("A. Prüfer")
    page = window.campaign
    page.refresh()
    seen = []

    def accept(dialog):
        dialog.asset.setCurrentIndex(dialog.asset.findData(press))
        seen.append((dialog.repeat.isVisible() or not dialog.repeat.isHidden(),
                     dialog.repeat.isChecked(), dialog.plan.isEnabled(), dialog.repeat.text()))
        return 1

    monkeypatch.setattr(CampaignDialog, "exec", accept)
    page.new_campaign()
    return {"page": page, "values": page.values, "seen": seen, "cabinet": cabinet,
            "campaign": page.campaign_id}


def _point_rows(values):
    table = values.table
    return [row for row in range(table.rowCount()) if table.item(row, 0).data(POINT_ID)]


def test_the_dialog_offers_to_repeat_the_last_inspection(repeat):
    shown, checked, plan_enabled, text = repeat["seen"][0]
    assert shown and checked and not plan_enabled
    assert text.startswith("Wie die Prüfung vom ") and text.endswith("(2 Punkte)")


def test_open_points_stand_in_the_table_and_count_in_the_head(repeat):
    values, page = repeat["values"], repeat["page"]
    assert len(_point_rows(values)) == 2
    assert values.table.item(_point_rows(values)[0], 0).text() == "offen"
    assert "2 offen" in values.count.text()
    assert "2 offen" in page.header.checks.text()
    assert not page.guided.isVisibleTo(page)  # filled in any order, not led through


def test_a_chosen_point_shows_what_to_take_and_where_readings_go(repeat):
    values, page = repeat["values"], repeat["page"]
    riso = next(row for row in _point_rows(values)
                if values.table.item(row, 5).text() == "RISO")
    values.table.selectRow(riso)
    assert values.point.isVisibleTo(values.detail) and not values.editor.isVisibleTo(values.detail)
    assert "RISO - Nennspannung: 500 V" in values.point.settings.text()
    assert page.place_target(repeat["campaign"]) == repeat["cabinet"]


def test_a_reading_takes_its_point_and_shows_last_time(repeat, app):
    values, page = repeat["values"], repeat["page"]
    app.service.insert_imported(repeat["campaign"], _riso("new", "5MΩ"), "device:x",
                                datetime(2026, 5, 4, 9), None, None, None, repeat["cabinet"])
    page._data_changed()
    assert len(_point_rows(values)) == 1
    row = next(row for row in range(values.table.rowCount())
               if values.table.item(row, VALUES).text().startswith("RISO"))
    values.table.selectRow(row)
    assert "RISO 20MΩ" in values.compare.before.text()
    assert "deutlich niedriger" in values.compare.notable.text()


def test_questions_are_answered_and_points_left_out_with_a_reason(repeat, monkeypatch):
    values = repeat["values"]
    rows = _point_rows(values)
    check = next(row for row in rows if values.table.item(row, 5).text() == "Ist der Schrank zu?")
    values.table.selectRow(check)
    values.point.no_button.click()
    rows = _point_rows(values)
    assert len(rows) == 1
    values.table.selectRow(rows[0])

    def leave(overlay):
        overlay.reason.setPlainText("Schrank verschlossen")
        return 1

    monkeypatch.setattr(ReasonOverlay, "exec", leave)
    values.point.skip_button.click()
    row = _point_rows(values)[0]
    assert values.table.item(row, 0).text() == "ausgelassen"
    assert "Schrank verschlossen" in values.table.item(row, VALUES).text()
    assert repeat["page"].app.service.blockers(repeat["campaign"]) == []


def test_an_inspection_without_points_is_not_offered_for_repeating(app, window):
    press = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    app.service.close(app.service.create(press, "Leer", "Prüfer"))
    dialog = CampaignDialog(app, window)
    dialog.asset.setCurrentIndex(dialog.asset.findData(press))
    assert dialog.previous is None and dialog.repeat.isHidden() and dialog.plan.isEnabled()
