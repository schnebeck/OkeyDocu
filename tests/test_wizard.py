# EasyMeasurement - tests/test_wizard.py
# Going through a plan point by point.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from easymeasurement.campaign.plan import parse_plan
from easymeasurement.ui.growing_edit import GrowingEdit
from easymeasurement.ui.guided_pages import ReasonOverlay
from easymeasurement.ui.measurement_overlays import MeasurementOverlay

PLAN = parse_plan("""
key: sight
title: Sichtprüfung
released: true
steps:
  - {key: a, kind: note, title: Vorbereitung, text: Anlage freischalten.}
  - {key: b, kind: check, title: "Abdeckung vorhanden?"}
  - {key: c, kind: check, title: "Schäden sichtbar?", expected: "no"}
  - {key: d, function: rlo}
""")


@pytest.fixture
def page(window, app, asset):
    """A manual campaign: the wizard works without any instrument."""
    campaign = app.service.create(asset, "T", "Anna", PLAN)
    window.campaign.refresh()
    window.campaign.enter(campaign)
    window.campaign.run_plan(app.service.plan_blocks(campaign)[0])
    return window.guided


def at_question(page):
    page.next_button.click()
    assert page.pages.currentWidget() is page.check_page
    return page.check_page


def test_wizard_opens_for_a_plan_without_an_instrument(window, page):
    assert window.campaign.current_work() is page


def test_position_is_always_in_sight(page):
    assert "Punkt 1 von 4" in page.position.text()


def test_note_is_shown_and_passed_with_next(page):
    assert page.pages.currentWidget() is page.note_page
    assert page.note_page.text.text() == "Anlage freischalten."
    page.next_button.click()
    assert "Punkt 2 von 4" in page.position.text()
    assert page.app.service.steps(page.campaign_id)[0]["status"] == "done"


def test_back_is_there_from_the_second_point_on(page):
    assert not page.back_button.isEnabled()
    page.next_button.click()
    page.back_button.click()
    assert "Punkt 1 von 4" in page.position.text()


def test_next_waits_for_an_answer(page):
    at_question(page)
    assert not page.next_button.isEnabled()


def test_the_expected_answer_goes_straight_on(page):
    check = at_question(page)
    check.buttons["yes"].click()
    assert "Punkt 3 von 4" in page.position.text()
    assert page.app.service.step_answer(page.app.service.steps(page.campaign_id)[1]["id"])[0] == "yes"


def test_the_expected_answer_can_be_a_no(page):
    at_question(page).buttons["yes"].click()
    page.check_page.buttons["no"].click()
    assert "Punkt 4 von 4" in page.position.text()


def test_another_answer_stays_for_a_comment(window, page):
    check = at_question(page)
    window.activateWindow()
    check.buttons["no"].click()
    assert "Punkt 2 von 4" in page.position.text()
    assert page.next_button.isEnabled()
    check.comment.setPlainText("fehlt")
    page.next_button.click()
    steps = page.app.service.steps(page.campaign_id)
    assert page.app.service.step_answer(steps[1]["id"]) == ("no", "fehlt")


def test_skipping_needs_a_reason(page):
    check = at_question(page)
    check.buttons["skip"].click()
    assert not page.next_button.isEnabled()
    assert "begründen" in check.hint.text()
    check.comment.setPlainText("nicht zugänglich")
    assert page.next_button.isEnabled()
    assert check.hint.text() == ""
    page.next_button.click()
    assert page.app.service.steps(page.campaign_id)[1]["status"] == "skipped"


def test_going_back_shows_what_was_answered(page):
    check = at_question(page)
    check.buttons["no"].click()
    check.comment.setPlainText("fehlt")
    page.next_button.click()
    page.back_button.click()
    assert check.choice == "no"
    assert check.comment.toPlainText() == "fehlt"


def test_passing_an_unchanged_answer_leaves_it_alone(page):
    check = at_question(page)
    check.buttons["yes"].click()
    page.back_button.click()
    service = page.app.service
    step = service.steps(page.campaign_id)[1]
    before = service.measurements(page.campaign_id, step["id"])[0]["id"]
    page.next_button.click()
    assert service.measurements(page.campaign_id, step["id"])[0]["id"] == before


def test_keys_answer_without_the_mouse(page):
    check = at_question(page)
    QTest.keyClick(check, Qt.Key.Key_J)
    assert "Punkt 3 von 4" in page.position.text()


def test_a_key_in_the_comment_field_only_writes(page):
    check = at_question(page)
    check.comment.setFocus()
    QTest.keyClick(check.comment, Qt.Key.Key_J)
    assert check.choice == ""
    assert check.comment.toPlainText() == "j"


def test_enter_goes_on_once_an_answer_is_given(page):
    check = at_question(page)
    QTest.keyClick(check, Qt.Key.Key_Return)
    assert "Punkt 2 von 4" in page.position.text()
    check.buttons["no"].click()
    QTest.keyClick(check, Qt.Key.Key_Return)
    assert "Punkt 3 von 4" in page.position.text()


def test_refreshing_keeps_the_point_on_screen(page):
    page.next_button.click()
    page.next_button.setEnabled(False)
    page.reload()
    assert "Punkt 2 von 4" in page.position.text()


def test_the_list_marks_a_failed_answer(page):
    check = at_question(page)
    check.buttons["no"].click()
    page.next_button.click()
    assert page.steps.item(1).text().startswith("✗")


def test_all_done_says_what_comes_next(page):
    at_question(page).buttons["yes"].click()
    page.check_page.buttons["no"].click()
    page.skip("nicht messbar")
    assert "nacharbeiten" in page.position.text()


def test_measuring_step_can_be_left_out_with_a_reason(page, monkeypatch):
    def fill(overlay):
        overlay.reason.setPlainText("nicht messbar")
        return 1

    monkeypatch.setattr(ReasonOverlay, "exec", fill)
    page.steps.setCurrentRow(3)
    page.skip_button.click()
    assert page.app.service.steps(page.campaign_id)[3]["note"] == "nicht messbar"


def test_a_reason_is_required(qtbot):
    overlay = ReasonOverlay()
    qtbot.addWidget(overlay)
    assert not overlay.ok_button.isEnabled()
    overlay.reason.setPlainText("x")
    assert overlay.ok_button.isEnabled()


def test_typed_measurement_lands_in_the_shown_step(window, page, app, monkeypatch):
    page.steps.setCurrentRow(3)
    page.device_set.setChecked(True)
    for index in range(page.wiring.total):
        page.wiring.wire_clicked(index)
    page.confirm_button.click()
    step = app.service.steps(page.campaign_id)[3]

    def fill(dialog):
        dialog.function.setCurrentIndex(dialog.function.findData("rlo"))
        return 1

    monkeypatch.setattr(MeasurementOverlay, "exec", fill)
    window.campaign.values.manual_action.trigger()
    assert len(app.service.measurements(page.campaign_id, step["id"])) == 1
    assert app.service.open_measurements(page.campaign_id) == []


def test_field_starts_with_one_line_and_grows(qtbot):
    field = GrowingEdit()
    qtbot.addWidget(field)
    field.resize(300, field.height())
    field.show()
    one_line = field.height()
    field.setPlainText("Zeile\n" * 3)
    QApplication.processEvents()
    assert field.height() > one_line


def test_field_stops_growing(qtbot):
    field = GrowingEdit()
    qtbot.addWidget(field)
    field.show()
    field.setPlainText("Zeile\n" * 6)
    QApplication.processEvents()
    tall = field.height()
    field.setPlainText("Zeile\n" * 60)
    QApplication.processEvents()
    assert field.height() == tall



def test_field_grows_while_one_long_line_wraps(qtbot):
    """Typed without Enter, a long text wraps; every wrapped line stays in view."""
    field = GrowingEdit()
    qtbot.addWidget(field)
    field.resize(160, field.height())
    field.show()
    one_line = field.height()
    qtbot.keyClicks(field, "Das Schutzorgan muss trennen, damit der Test gelingt")
    QApplication.processEvents()
    assert field.height() > one_line
    lines = round(field.document().documentLayout().documentSize().height())
    assert lines > 1
    assert field.viewport().height() >= lines * field.fontMetrics().lineSpacing()
