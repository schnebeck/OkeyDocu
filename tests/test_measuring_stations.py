# OkeyDocu - tests/test_measuring_stations.py
# Supply, settings and measuring in a guided measurement, and the short run of a repeat.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace
from datetime import datetime

import pytest

from okeydocu.devices.base import LiveReading
from okeydocu.devices.guide import CONFIGURE, CONNECT, MEASURE, PLACE, PREPARE, SELECT
from okeydocu.devices.profitest_prime.selector import selector_position
from okeydocu.devices.profitest_prime.guides import MAINS, flow
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.l10n import speaking
from okeydocu.ui.measuring_window import MeasuringWindow


@pytest.fixture
def plant(app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    switch = app.db.add_asset(customer, "rcd", "FI Steuerung", machine, identifier="=K1-F1")
    app.db.set_asset_features(switch, {"rcd_type": "A", "rated_residual_current": "30",
                                       "rated_current": "25", "number_of_poles": "4"})
    campaign = app.service.create(machine, "Prüfung", "Tester")
    return {"campaign": campaign, "machine": machine, "switch": switch}


def opened(qtbot, app, plant, function="rcd_time", asset="switch", repeat=False):
    with speaking("de"):
        shown = MeasuringWindow(app, plant["campaign"], DRIVER_KEY, function, plant[asset],
                                repeat=repeat)
    qtbot.addWidget(shown)
    shown.resize(1440, 1020)
    shown.show()
    return shown


def reading(function: str) -> LiveReading:
    return LiveReading(SimulatedMeter(seed=1).simulate_measurement(function), datetime.now())


def test_the_battery_is_enough_unless_the_guide_needs_the_mains(qtbot, app, plant):
    window = opened(qtbot, app, plant)
    with speaking("de"):
        window.go_to(PREPARE)
    assert window.bench.panel.pointed == ("mains-inlet", "mains-switch")
    assert "reicht der Akku" in window.step_text.text()
    window.guide = replace(window.guide, flow=flow(MAINS))
    window.flow = window.guide.flow
    with speaking("de"):
        window.go_to(PREPARE)
    assert window.bench.panel.pointed == ("mains-inlet", "mains-switch")
    assert "Netzversorgung" in window.step_text.text()
    assert "Glimmlampe im Netzschalter" in window.step_text.text()


def test_the_settings_name_what_the_rcd_states_and_close_in_on_the_display(qtbot, app, plant):
    window = opened(qtbot, app, plant)
    with speaking("de"):
        window.go_to(CONFIGURE)
    text = window.step_text.text()
    assert "=K1-F1 FI Steuerung gibt an" in text
    assert "<b>A</b>" in text and "<b>30 mA</b>" in text and "<b>25 A</b>" in text
    assert window.bench.panel.pointed == ("soft-1", "soft-2", "soft-3")
    assert window.bench.leads_layer.isHidden()
    whole = window.bench.panel.front.viewBoxF()
    assert window.bench.panel._zoom.endValue().width() < whole.width() / 2
    window.go_to(MEASURE)
    assert not window.bench.leads_layer.isHidden()


def test_the_last_station_waits_for_the_result_of_its_own_measurement(qtbot, app, plant):
    window = opened(qtbot, app, plant)
    with speaking("de"):
        window.go_to(MEASURE)
        assert "Warte auf das Ergebnis" in window.step_text.text()
        assert window.bench.panel.pointed == ("key-start", "key-idn", "soft-5")
        window.show_reading(reading("rlo"))
        assert window.reading is None
        window.show_reading(reading("rcd_time"))
        text = window.step_text.text()
    assert "Empfangen" in text and window.bench.panel.pointed == ()
    assert window.next.text() == "Fertig ▶"


def kinds_reached(window) -> list[str]:
    reached = [window.kind]
    while window.index < window.count - 1:
        window.next.click()
        reached.append(window.kind)
    return reached


def test_a_repeat_passes_by_the_switch_set_right_and_the_leads_in_place(qtbot, app, plant):
    app.service.add_measurement(plant["campaign"], "rcd_time", [], asset_id=plant["switch"])
    window = opened(qtbot, app, plant, repeat=True)
    assert all(not chip.isHidden() for chip in window.bar.chips[:window.count])
    assert "Wiederholmessung" in window.head.text()
    window.show_selector(selector_position(window.guide.selector))
    window.form.fields["n_terminal"].setEditText("links")
    with speaking("de"):
        reached = kinds_reached(window)
    assert reached == [PLACE, PREPARE, CONFIGURE, MEASURE]
    assert window.bench.progress == len(window.guide.leads)
    assert app.db.asset_features(plant["switch"])["n_terminal"] == "left"


def test_a_repeat_shows_the_switch_set_wrong_and_leads_without_an_earlier_run(qtbot, app,
                                                                             plant):
    window = opened(qtbot, app, plant, repeat=True)
    window.show_selector(selector_position(12))
    with speaking("de"):
        reached = kinds_reached(window)
    assert reached == [PLACE, SELECT, CONNECT, PREPARE, CONFIGURE, MEASURE]


def test_the_button_that_goes_on_keeps_its_width_and_place(qtbot, app, plant):
    window = opened(qtbot, app, plant)
    places = set()
    with speaking("de"):
        for index in range(window.count):
            window.go(index)
            qtbot.wait(10)
            places.add((window.next.width(), window.next.mapTo(window, window.next.rect()
                                                                .topLeft()).x()))
    assert len(places) == 1


@pytest.mark.parametrize("function, kind, terminals", [
    ("u", "main_switch", {"pe", "in_l1", "in_n"}), ("rlo", "cee_plug", {"pe_pin", "body"})])
def test_voltage_and_protective_conductor_have_their_own_test_points(qtbot, app, plant,
                                                                      function, kind, terminals):
    window = opened(qtbot, app, plant, function, "machine")
    window.go_to(MEASURE)
    window.bench.grab()
    assert window.guide.test_object == kind
    assert set(window.bench.anchors) >= terminals
    assert window.place.asset_id == plant["machine"]


def test_one_line_conductor_without_n_takes_two_leads_and_advises_against_auto(
        qtbot, app, plant):
    app.db.set_asset_features(plant["machine"], {"line_conductors": "1",
                                                 "n_conductor": "without N"})
    window = opened(qtbot, app, plant, "u", "machine")
    assert window.place.poles == 2 and window.place.has_n is False
    assert [lead.plug for lead in window.guide.leads] == ["3", "1"]
    with speaking("de"):
        window.go_to(CONFIGURE)
    assert "Messstrecke von Hand wählen" in window.step_text.text()


def test_what_is_stated_above_stands_in_the_empty_field(qtbot, app, plant):
    hall = app.db.asset(plant["machine"])["parent_id"]
    cabinet = app.db.add_asset(app.db.asset(plant["machine"])["customer_id"],
                               "distribution_board", "Schrank", plant["machine"])
    app.db.set_asset_features(plant["machine"], {"line_conductors": "3"})
    plant["cabinet"] = cabinet
    with speaking("de"):
        window = opened(qtbot, app, plant, "u", "cabinet")
    field = window.form.fields["line_conductors"]
    assert field.lineEdit().placeholderText() == "3, wie übergeordnet angegeben"
    assert "fde2c4" not in field.styleSheet()
    assert hall is None and window.place.poles == 4


def test_the_leads_are_painted_anew_while_the_panel_moves_out(qtbot, app, plant, monkeypatch):
    window = opened(qtbot, app, plant)
    zoom = window.bench.panel._zoom
    with speaking("de"):
        window.go_to(CONFIGURE)
    qtbot.waitUntil(lambda: zoom.state() == zoom.State.Stopped, timeout=3000)
    painted = []
    monkeypatch.setattr(window.bench.leads_layer, "update", lambda *a: painted.append(a))
    window.go_to(MEASURE)
    qtbot.waitUntil(lambda: zoom.state() == zoom.State.Stopped, timeout=3000)
    assert len(painted) > 2 and all(call == () for call in painted)
