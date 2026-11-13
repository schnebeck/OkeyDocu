# OkeyDocu - tests/test_measurement_window.py
# Measurement rules in the window and in closed campaigns.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.store import CampaignClosed
from okeydocu.ui.main_window import MainWindow


# Closed campaigns ------------------------------------------------------------


def closed(service, asset_id):
    campaign = service.create(asset_id, "T", "P")
    measurement = service.add_measurement(campaign, "other", [])
    service.close(campaign)
    return measurement


def test_closed_campaign_cannot_be_edited(service, asset_id):
    measurement = closed(service, asset_id)
    with pytest.raises(CampaignClosed):
        service.edit_measurement(measurement, {"comment": "neu"})
    assert service.measurement_changes(measurement) == []


def test_closed_campaign_cannot_lose_a_measurement(service, asset_id):
    measurement = closed(service, asset_id)
    with pytest.raises(CampaignClosed):
        service.delete_measurement(measurement)
    assert service.measurement_changes(measurement) == []


# In the window ---------------------------------------------------------------


@pytest.fixture
def window(qtbot, app):
    main = MainWindow(app)
    qtbot.addWidget(main)
    main.show()
    main.open_page(main.measurements)
    yield main
    main.campaign.shut_down()


def one_measurement(window, app, close=False):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "T", "P")
    measurement = app.service.add_measurement(
        campaign, "rlo", [ResultValue("rlo", "RLO", Quantity.parse("0.21Ω"))],
        datetime(2026, 5, 4, 10, 0), Verdict.PASSED, comment="alt",
    )
    if close:
        app.service.close(campaign)
    page = window.measurements
    page.reload_choices()
    page.refresh()
    page.table.selectRow(0)
    return page, measurement


def test_the_value_itself_is_not_open_to_editing(window, app):
    page, _ = one_measurement(window, app)
    values = page.editor.values
    assert values.item(0, 1).text() == "0.21Ω"
    assert not values.item(0, 1).flags() & Qt.ItemFlag.ItemIsEditable
    assert values.item(0, 2).flags() & Qt.ItemFlag.ItemIsEditable


def test_typing_writes_nothing_until_it_is_taken_over(window, app):
    page, measurement = one_measurement(window, app)
    page.editor.comment.setPlainText("neu")
    assert page.editor.pending.isVisible()
    assert app.service.measurements(stored_campaign(app, measurement))[0]["comment"] == "alt"
    page.editor.apply_button.click()
    assert app.service.measurements(stored_campaign(app, measurement))[0]["comment"] == "neu"
    assert not page.editor.pending.isVisible()


def test_only_what_was_touched_is_changed(window, app):
    page, measurement = one_measurement(window, app)
    editor = page.editor
    editor.verdict.setCurrentIndex(editor.verdict.findData("failed"))
    assert "Bewertung" in editor.pending_hint.text()
    editor.apply_button.click()
    assert [c["field"] for c in app.service.measurement_changes(measurement)] == ["verdict"]
    assert page.table.item(0, 8).text() == "nicht bestanden"


def test_a_text_fix_says_it_leaves_no_mark(window, app):
    page, _ = one_measurement(window, app)
    page.editor.location.setText("Schrank")
    page.editor.location.textEdited.emit("Schrank")
    assert "ohne Vermerk" in page.editor.pending_hint.text()


def test_a_limit_is_corrected_in_the_value_table(window, app):
    page, measurement = one_measurement(window, app)
    page.editor.values.item(0, 3).setText("<0.30Ω")
    page.editor.apply()
    value = app.service.values(measurement)[0]
    assert value["upper_limit"] == "<0.30Ω"
    assert value["raw"] == "0.21Ω"


def test_discarding_brings_back_what_is_stored(window, app):
    page, _ = one_measurement(window, app)
    page.editor.comment.setPlainText("verschrieben")
    page.editor.discard_button.click()
    assert page.editor.comment.toPlainText() == "alt"
    assert not page.editor.dirty


def test_moving_on_takes_the_edits_along(qtbot, window, app):
    page, measurement = one_measurement(window, app)
    campaign = stored_campaign(app, measurement)
    app.service.add_measurement(campaign, "other", [], datetime(2026, 5, 4, 11, 0))
    page.refresh()
    page.table.selectRow(0)
    page.editor.comment.setPlainText("mitgenommen")
    page.table.selectRow(1)
    assert app.service.measurements(campaign)[0]["comment"] == "mitgenommen"
    qtbot.waitUntil(lambda: page.table.currentRow() == 1)
    assert page.editor.comment.toPlainText() == ""


def test_a_double_click_puts_the_cursor_where_it_was(window, app):
    page, _ = one_measurement(window, app)
    page.table.cellDoubleClicked.emit(0, 4)
    assert QApplication.focusWidget() is page.editor.location


def test_closed_campaign_can_only_be_read(window, app):
    page, _ = one_measurement(window, app, close=True)
    assert page.editor.locked.isVisible()
    assert page.editor.comment.isReadOnly()
    assert not page.editor.verdict.isEnabled()
    assert not page.editor.values.item(0, 2).flags() & Qt.ItemFlag.ItemIsEditable


def stored_campaign(app, measurement):
    return app.db.one("SELECT campaign_id FROM measurements WHERE id=?", measurement)[0]


def test_buttons_follow_the_campaign_state(window, app):
    page, _ = one_measurement(window, app)
    assert page.edit_measurement.isEnabled()
    assert page.delete_measurement.isEnabled()


def test_closed_campaign_offers_no_editing(window, app):
    page, _ = one_measurement(window, app, close=True)
    assert not page.edit_measurement.isEnabled()
    assert not page.delete_measurement.isEnabled()


def test_deleting_asks_first(window, app):
    page, measurement = one_measurement(window, app)
    page.delete_measurement.click()  # the default answer in tests is no
    assert app.db.one("SELECT 1 FROM measurements WHERE id=?", measurement)


def test_deleting_after_confirmation(window, app, monkeypatch):
    page, measurement = one_measurement(window, app)
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    page.delete_measurement.click()
    assert app.db.one("SELECT 1 FROM measurements WHERE id=?", measurement) is None
    assert page.table.rowCount() == 0


def test_how_a_value_was_captured_is_shown(window, app):
    page, _ = one_measurement(window, app)
    assert page.table.item(0, 9).text() == "manuell"


def test_ctrl_enter_takes_over_and_escape_discards(qtbot, window, app):
    page, measurement = one_measurement(window, app)
    editor = page.editor
    editor.comment.setFocus()
    editor.comment.setPlainText("per Taste")
    qtbot.keyClick(editor.comment, Qt.Key.Key_Return, Qt.KeyboardModifier.ControlModifier)
    assert not editor.dirty
    editor.comment.setPlainText("weg damit")
    qtbot.keyClick(editor.comment, Qt.Key.Key_Escape)
    assert editor.comment.toPlainText() == "per Taste"


def test_the_wheel_does_not_turn_a_choice_it_passes(qtbot, window, app):
    page, _ = one_measurement(window, app)
    before = page.editor.verdict.currentIndex()
    page.table.setFocus()
    event = QWheelEvent(QPointF(5, 5), QPointF(5, 5), QPoint(0, 0), QPoint(0, -120),
                        Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                        Qt.ScrollPhase.NoScrollPhase, False)
    QApplication.sendEvent(page.editor.verdict, event)
    assert page.editor.verdict.currentIndex() == before


def test_a_new_reading_does_not_take_away_an_edit(window, app):
    page, measurement = one_measurement(window, app)
    values = window.campaign.values
    values.show_campaign(stored_campaign(app, measurement))
    values.table.selectRow(0)
    app.service.add_measurement(stored_campaign(app, measurement), "other", [])
    values.editor.comment.setPlainText("halb getippt")
    values.refresh()
    values.show_newest()
    assert values.editor.comment.toPlainText() == "halb getippt"


def test_keys_on_the_table_edit_and_delete(qtbot, window, app, monkeypatch):
    page, measurement = one_measurement(window, app)
    page.table.setFocus()
    qtbot.keyClick(page.table, Qt.Key.Key_Return)
    assert QApplication.focusWidget() is page.editor.comment
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    page.table.setFocus()
    qtbot.keyClick(page.table, Qt.Key.Key_Delete)
    assert app.db.one("SELECT 1 FROM measurements WHERE id=?", measurement) is None


def test_an_edit_on_a_record_closed_meanwhile_is_reported(window, app, monkeypatch):
    errors = []
    monkeypatch.setattr("okeydocu.ui.measurement_editing.show_error",
                        lambda _, text: errors.append(text))
    page, measurement = one_measurement(window, app)
    page.editor.comment.setPlainText("zu spät")
    app.service.close(stored_campaign(app, measurement))
    assert not page.editor.apply()
    assert "abgeschlossen" in errors[0]
    assert page.editor.comment.toPlainText() == "alt"
