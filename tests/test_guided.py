# EasyMeasurement - tests/test_guided.py
# The guided flow in the real window, with the simulator as instrument.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtWidgets import QMessageBox

from easymeasurement.reporting.archive import ReportError
from easymeasurement.reporting.sign import Pkcs12Signer
from easymeasurement.ui.confirm_overlay import ConfirmOverlay

from . import guided_helpers
from .guided_helpers import connect_all, run_step, shown

# pytest looks fixtures up by name in the test module.
page, window = guided_helpers.page, guided_helpers.window


def test_new_campaign_opens_on_the_first_step(page):
    assert page.steps.count() == 5
    assert page.steps.currentRow() == 0
    assert page.wiring.total == 2
    assert "Simulation" in page.banner.text()
    assert "Entwurf" in page.banner.text()


def test_measuring_needs_a_confirmed_setup(page):
    assert not page.simulate_button.isEnabled()
    connect_all(page)
    page.confirm_button.click()
    assert page.simulate_button.isEnabled()
    assert page.wiring.locked


def test_any_number_of_measurements_lands_on_the_step(page, window):
    connect_all(page)
    page.confirm_button.click()
    for _ in range(4):
        page.simulate_button.click()
    page.fetch_button.click()
    assert shown(page) == 4
    assert page.open_table.rowCount() == 0


def test_finishing_fetches_unfetched_readings_and_moves_on(page, window):
    run_step(page, readings=2)
    steps = window.app.service.steps(page.campaign_id)
    assert steps[0]["status"] == "done"
    assert len(window.app.service.measurements(page.campaign_id, steps[0]["id"])) == 2
    assert page.steps.currentRow() == 1


def test_wrong_rotary_position_ends_up_in_the_open_list(page):
    connect_all(page)
    page.confirm_button.click()
    page.simulate_function.setCurrentIndex(page.simulate_function.findData("zloop"))
    page.simulate_button.click()
    page.fetch_button.click()
    assert shown(page) == 0
    assert page.open_table.rowCount() == 1
    assert "passt nicht" in page.open_table.item(0, 3).text()


def test_open_measurement_can_be_assigned(page):
    connect_all(page)
    page.confirm_button.click()
    page.simulate_function.setCurrentIndex(page.simulate_function.findData("zloop"))
    page.simulate_button.click()
    page.fetch_button.click()
    page.open_table.setCurrentCell(0, 0)
    page.assign_button.click()
    assert page.open_table.rowCount() == 0
    assert shown(page) == 1


def test_step_with_no_measurement_asks_first(page, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.No)
    connect_all(page)
    page.confirm_button.click()
    page.next_button.click()
    assert page.steps.currentRow() == 0
    assert page.next_button.isEnabled()


def test_a_finished_step_can_be_measured_again(page, window):
    run_step(page)
    page.steps.setCurrentRow(0)
    page.confirm_button.click()
    page.simulate_button.click()
    page.next_button.click()
    step = window.app.service.steps(page.campaign_id)[0]
    assert len(window.app.service.measurements(page.campaign_id, step["id"])) == 2


def test_campaign_survives_a_restart_of_the_simulator(page, window):
    connect_all(page)
    page.confirm_button.click()
    window.app.devices.drivers.clear()
    page.simulate_button.click()
    page.fetch_button.click()
    assert shown(page) == 1


def test_complete_run_from_first_step_to_report(page, window, monkeypatch):
    def fail(_, text):
        raise AssertionError(text)

    monkeypatch.setattr("easymeasurement.ui.guided_actions.show_error", fail)
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(ConfirmOverlay, "exec", lambda self: 1)
    campaign = page.campaign_id
    run_step(page, readings=3)
    run_step(page, readings=1)
    run_step(page, readings=1)
    run_step(page, readings=2)
    page.skip("Stromkreis nicht abschaltbar")
    window.campaign.finish()
    app = window.app
    assert app.service.campaign(campaign)["status"] == "closed"
    assert window.campaign.current_work() is None
    window.measurements.refresh()
    assert window.measurements.table.rowCount() == 7
    report_id = app.archive.reports(campaign)[0]["id"]
    window.reports.refresh()
    assert window.reports.table.rowCount() == 1
    with pytest.raises(ReportError, match="simulierten"):
        app.archive.sign(report_id, Pkcs12Signer("x", "y"))


def test_campaign_cannot_close_with_open_steps(page, window, qtbot):
    overlay = ConfirmOverlay(window.app, window.app.service.campaign(page.campaign_id))
    qtbot.addWidget(overlay)
    assert "Schritt offen" in overlay.open_points.text()
    assert not overlay.ok_button.isEnabled()


# The rotary switch -----------------------------------------------------------


def live_session(page, window):
    window.campaign.enter(page.campaign_id)
    return window.campaign.session.driver


def tick_setup(page):
    connect_all(page)
    page.device_set.setChecked(False)
    page.device_set.click()


def test_a_step_says_when_the_switch_is_wrong(page, window):
    driver = live_session(page, window)
    driver.selector = "zloop"
    tick_setup(page)
    assert "⚠" in page.selector_hint.text()
    assert "ZLOOP" in page.selector_hint.text()


def test_a_step_confirms_the_right_switch(page, window):
    driver = live_session(page, window)
    function = window.app.service.plan_step(page._step()).function
    driver.selector = function
    tick_setup(page)
    assert "✓" in page.selector_hint.text()


def test_a_wrong_switch_does_not_stop_the_operator(page, window):
    live_session(page, window).selector = "zloop"
    tick_setup(page)
    assert page.confirm_button.isEnabled()


def test_the_switch_is_left_alone_while_measuring(page, window, monkeypatch):
    driver = live_session(page, window)
    connect_all(page)
    page.confirm_button.click()

    def must_not_run():
        raise AssertionError("Abfrage während der Messung")

    monkeypatch.setattr(driver, "read_selector", must_not_run)
    page._read_selector()


def test_a_connection_that_ended_badly_is_reported_once(page, window, monkeypatch):
    errors = []
    monkeypatch.setattr(
        "easymeasurement.ui.campaign_actions.show_error", lambda _, text: errors.append(text)
    )
    driver = live_session(page, window)
    driver.stop_warning = "Bitte einschalten"
    window.campaign.pause()
    window.campaign.resume()
    window.campaign.pause()
    assert errors == ["Bitte einschalten"]
