# OkeyDocu - tests/test_climate_guide.py
# A climate sensor booked beside the simulator, and its guided measurement.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The simulated sensor's clock is driven by hand, so it settles without waiting."""

import pytest

from okeydocu.devices.guide import IDENTIFY, MEASURE, SETTLE
from okeydocu.l10n import speaking
from okeydocu.ui.instrument_booking import InstrumentBookingOverlay

from .workspace_helpers import start, with_asset


@pytest.fixture
def clock(monkeypatch):
    now = [1000.0]
    monkeypatch.setattr("okeydocu.devices.climate.simulated.time.monotonic", lambda: now[0])
    return now


@pytest.fixture
def page(window, app, monkeypatch, clock):
    with_asset(window, app)
    with speaking("de"):
        start(window, monkeypatch, simulated=True)
    return window.campaign


def book_sensor(page, app):
    overlay = InstrumentBookingOverlay(app, page.campaign_id, page)
    index = next(index for index in range(overlay.offered.count())
                 if overlay.offered.itemData(index).key == "climate-simulator")
    overlay.offered.setCurrentIndex(index)
    overlay.book()
    assert overlay.changed
    page.show_campaign(page.campaign_id)
    return next(booked.slot for booked in app.service.instruments(page.campaign_id) if booked.slot)


def test_a_sensor_booked_beside_is_guided_and_its_reading_filed_as_its_own(page, app, clock,
                                                                         qtbot):
    slot = book_sensor(page, app)
    starter = page.free.starter
    assert starter.slot_of("ambient") == slot and starter.slot_of("u") == 0
    starter.choice.setCurrentIndex(starter.choice.findData("ambient"))
    starter.button.click()
    window = page.guide_window
    window._choose(window.root)  # measured at the installation itself
    window.next.click()
    assert window.kind == IDENTIFY and window.show_button.isVisibleTo(window)
    with qtbot.waitSignal(window.pointed, timeout=5000) as shown:
        window.show_button.click()
    assert "mit einem Gesicht" in shown.args[0] and shown.args[0] in window.step_text.text()
    window.go_to(SETTLE)
    window._sensor_tick()
    assert not window.next.isEnabled()
    clock[0] += 60
    for _ in range(10):
        clock[0] += 1
        window._sensor_tick()
    assert window.next.isEnabled()
    window.go_to(MEASURE)
    assert window.take_button.isVisibleTo(window) and window.take_button.isEnabled()
    window.take_button.click()
    rows = [row for row in app.service.measurements(page.campaign_id)
            if row["function"] == "ambient"]
    assert len(rows) == 1 and rows[0]["source"] == "device:climate-simulator"
    assert window.reading is not None and not window.take_button.isVisibleTo(window)
    assert app.service.has_readings(page.campaign_id, slot)
    window.next.click()


def test_a_sensor_leaves_the_campaign_only_while_it_has_not_measured(page, app):
    slot = book_sensor(page, app)
    overlay = InstrumentBookingOverlay(app, page.campaign_id, page)
    overlay.booked.setCurrentRow(1)
    assert overlay.release_button.isEnabled()
    overlay.booked.setCurrentRow(0)
    assert not overlay.release_button.isEnabled()  # the campaign's own instrument stays
    overlay.booked.setCurrentRow(1)
    overlay.release()
    assert app.service.instrument(page.campaign_id, slot) is None
