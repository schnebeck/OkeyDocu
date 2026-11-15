# OkeyDocu - tests/test_guide_flows.py
# Each instrument's guide brings its own flow of stations; the window follows it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace
from datetime import datetime

import pytest

from okeydocu.devices.base import LiveReading, SelectorPosition
from okeydocu.devices.guide import MEASURE, PLACE, SELECT, Station
from okeydocu.devices.profitest_prime.guides import GUIDES as PRIME
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.l10n import speaking
from okeydocu.ui.measuring_window import MeasuringWindow


@pytest.fixture
def campaign(app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    return {"campaign": app.service.create(machine, "Prüfung", "Tester"), "machine": machine}


def opened(qtbot, app, campaign, driver, function="u"):
    with speaking("de"):
        window = MeasuringWindow(app, campaign["campaign"], driver, function,
                                 campaign["machine"])
    qtbot.addWidget(window)
    window.show()
    return window


def test_the_profitest_runs_six_stations_the_simulator_three(qtbot, app, campaign):
    prime = opened(qtbot, app, campaign, "profitest-prime")
    simulator = opened(qtbot, app, campaign, "simulator")
    assert len(prime.flow) == 6 and prime.has_dial
    assert simulator.guide.kinds() == (PLACE, SELECT, MEASURE)
    assert [chip.text() for chip in simulator.bar.chips] == ["1  Anlage", "2  Funktion",
                                                              "3  Messen"]
    assert not simulator.bench and not simulator.has_dial


def test_without_a_panel_the_window_shows_the_test_point_and_the_words(qtbot, app, campaign):
    window = opened(qtbot, app, campaign, "simulator")
    with speaking("de"):
        window.go_to(SELECT)
    assert window.left.currentWidget() is window.scene
    assert "Messung simulieren" in window.step_text.text()
    window.show_selector(SelectorPosition("U", frozenset({"u"})))
    qtbot.waitUntil(lambda: window.kind == MEASURE, timeout=3000)
    reading = SimulatedMeter(seed=2).simulate_measurement("u", datetime(2026, 11, 15, 9))
    window.show_reading(LiveReading(reading, datetime(2026, 11, 15, 9)))
    assert window.reading is not None


def test_a_flow_runs_in_the_order_and_number_its_driver_gives(qtbot, app, campaign,
                                                              monkeypatch):
    short = replace(PRIME["u"], flow=(Station(PLACE), Station(MEASURE, "Ablesen")))
    monkeypatch.setitem(PRIME, "u", short)
    window = opened(qtbot, app, campaign, "profitest-prime")
    assert [chip.text() for chip in window.bar.chips] == ["1  Anlage", "2  Ablesen"]
    window.next.click()
    assert window.kind == MEASURE and window.next.text() == "Fertig ▶"
