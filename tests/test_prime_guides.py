# OkeyDocu - tests/test_prime_guides.py
# Every guide of the PROFITEST PRIME runs through its stations on its own test point.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.devices.guide import CONFIGURE, CONNECT, MEASURE, PREPARE, SELECT
from okeydocu.devices.profitest_prime import screens
from okeydocu.devices.profitest_prime.guides import GUIDES as PRIME
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.devices.profitest_prime.panel import DRAWING
from okeydocu.devices.profitest_prime.selector import selector_position
from okeydocu.devices.registry import driver_info
from okeydocu.l10n import speaking
from okeydocu.ui.measuring_window import MeasuringWindow

LOOPS = ("zloop", "zloop_dc", "zloop_rlo", "zloop_half")
FUNCTIONS = ("u", "rlo", "rlo_25a", "riso", "riso_ramp", "rcd_time", "rcd_current", "i_ramp",
             *LOOPS, "ures")


def opened(qtbot, app, function):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    campaign = app.service.create(machine, "Prüfung", "Tester")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, DRIVER_KEY, function, machine)
    qtbot.addWidget(window)
    window.resize(1440, 1020)
    window.show()
    return window


def softkeys(guide, position=None) -> tuple[str, ...]:
    view = guide.screen_at(position)
    rows = [view.softkey(action.key) for action in guide.settings if action.key is not None]
    return tuple(DRAWING.softkeys[row] for row in rows if row is not None)


def test_the_driver_offers_a_guide_for_each_of_these_functions():
    assert tuple(PRIME) == FUNCTIONS == driver_info(DRIVER_KEY).guided
    assert len({guide.selector for guide in PRIME.values()}) == len(PRIME)


@pytest.mark.parametrize("function", FUNCTIONS)
def test_a_guide_runs_its_stations_and_its_probes_find_their_places(qtbot, app, function):
    window = opened(qtbot, app, function)
    with speaking("de"):
        for index in range(1, window.count):
            window.go(index)
            assert window.step_text.text()
    assert window.kind == MEASURE
    window.bench.grab()
    guide = window.guide
    assert {lead.terminal for lead in guide.leads} <= set(window.bench.anchors)
    assert window.bench.panel.screen == guide.screen_at(None, measured=True)
    assert window.bench.panel.target == guide.selector


def test_the_25_a_measurement_asks_for_the_mains_the_others_run_on_the_battery(qtbot, app):
    with speaking("de"):
        strong = opened(qtbot, app, "rlo_25a")
        strong.go_to(PREPARE)
        assert "Netzversorgung" in strong.step_text.text()
        weak = opened(qtbot, app, "rlo")
        weak.go_to(PREPARE)
        assert "reicht der Akku" in weak.step_text.text()


def test_each_loop_position_has_a_guide_with_its_own_probes_and_settings():
    plain, direct, combined, reduced = loops = [PRIME[function] for function in LOOPS]
    assert softkeys(plain) == ("soft-1", "soft-3", "soft-4")
    for guide in (direct, combined, reduced):
        assert softkeys(guide) == ("soft-1", "soft-2", "soft-3", "soft-4")
        assert guide.test_object == "rcd" and guide.owner_feature == "rcd_type"
    assert [len(guide.leads) for guide in loops] == [2, 3, 3, 2]
    assert {lead.probe: lead.terminal for lead in direct.leads} == {
        "L (L1)": "out_l", "N (L3)": "out_n", "PE (L2)": "pe"}
    assert {lead.probe: lead.terminal for lead in combined.leads} == {
        "L (L1)": "out_l", "N (L3)": "pe", "PE (L2)": "out_n"}
    assert combined.screen == screens.ZLOOP_COMBINED and reduced.screen == screens.ZLOOP_REDUCED


def test_a_loop_guide_is_served_by_its_own_position_only(qtbot, app):
    for function in LOOPS:
        guide = PRIME[function]
        assert [value for value in (20, 21, 22, 23) if guide.served_at(value)] == [guide.selector]
        assert not selector_position(guide.selector).rules_out(function)
    with speaking("de"):
        window = opened(qtbot, app, "zloop_dc")
        window.go_to(SELECT)
        window.show_selector(selector_position(20))
        assert "steht auf" in window.step_text.text()
        window.show_selector(selector_position(21))
        assert "richtig" in window.step_text.text()


def test_the_combined_loop_measurement_warns_that_n_and_pe_change_places(qtbot, app):
    with speaking("de"):
        window = opened(qtbot, app, "zloop_rlo")
        window.go_to(CONNECT)
    text = window.step_text.text()
    assert "Kabel 1, 2, 3" in text and "tauschen" in text
    assert text.index("N (L3) an die PE-Schiene") < text.index("PE (L2) an die Abgangsklemme N")


def test_the_rcd_guides_differ_in_position_and_in_what_the_trip_measures(qtbot, app):
    time, current, both = PRIME["rcd_time"], PRIME["rcd_current"], PRIME["i_ramp"]
    assert softkeys(time) == softkeys(current) == ("soft-1", "soft-2", "soft-3")
    assert softkeys(both) == softkeys(time, 19) == softkeys(current, 19) == ("soft-2", "soft-3")
    with speaking("de"):
        window = opened(qtbot, app, "i_ramp")
        window.go_to(CONFIGURE)
        assert window.bench.panel.pointed == ("soft-2", "soft-3")
        window.go_to(MEASURE)
    assert "Auslösestrom und Auslösezeit" in window.step_text.text()


def test_the_insulation_keeps_the_probes_on_until_the_test_point_is_discharged(qtbot, app):
    for function in ("riso", "riso_ramp"):
        with speaking("de"):
            window = opened(qtbot, app, function)
            window.go_to(MEASURE)
        text = window.step_text.text()
        assert text.index("ON/START") < text.index("unter 10 V") < text.index("Teilen")
        assert not window.guide.live
    assert softkeys(PRIME["riso_ramp"]) == ("soft-1", "soft-2", "soft-3", "soft-4")
