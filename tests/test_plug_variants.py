# OkeyDocu - tests/test_plug_variants.py
# A machine supplied through a Schuko plug is measured dead at its Schuko plug.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.devices.guide import MEASURE
from okeydocu.devices.profitest_prime.guides import GUIDES
from okeydocu.l10n import speaking
from okeydocu.ui.measuring_window import MeasuringWindow

AT_THE_PLUG = ("rlo", "rlo_25a", "riso", "riso_ramp")
SCHUKO = {"supply_connection": "Schuko plug"}


def opened(qtbot, app, function, child_kind=None, **features):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Bohrmaschine")
    app.db.set_asset_features(machine, features)
    place = machine
    if child_kind:
        place = app.db.add_asset(customer, child_kind, "Motor", parent_id=machine)
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    window = MeasuringWindow(app, campaign, "profitest-prime", function, place)
    qtbot.addWidget(window)
    window.resize(1440, 1020)
    window.show()
    return window


@pytest.mark.parametrize("function", AT_THE_PLUG)
def test_a_schuko_plug_takes_the_variant_with_the_same_settings(function):
    guide = GUIDES[function]
    schuko = guide.suited(SCHUKO.get)
    assert guide.test_object == "cee_plug" and schuko.test_object == "schuko_plug"
    assert schuko.function == function and schuko.selector == guide.selector
    assert schuko.settings == guide.settings and schuko.steps == guide.steps
    assert guide.suited({"supply_connection": "CEE plug"}.get) is guide
    assert guide.suited(lambda key: "") is guide


@pytest.mark.parametrize("function", AT_THE_PLUG)
def test_the_probes_find_their_places_on_the_schuko_plug(qtbot, app, function):
    window = opened(qtbot, app, function, **SCHUKO)
    for index in range(1, window.count):
        window.go(index)
    assert window.kind == MEASURE
    window.bench.grab()
    assert window.guide.test_object == "schuko_plug"
    assert {lead.terminal for lead in window.guide.leads} <= set(window.bench.anchors)


def test_an_element_below_the_machine_takes_the_plug_stated_above(qtbot, app):
    window = opened(qtbot, app, "rlo", child_kind="electric_engine", **SCHUKO)
    assert window.guide.test_object == "schuko_plug"


@pytest.mark.parametrize("function, drawing", [("rlo", "supply_pe"), ("riso", "main_switch_on")])
def test_a_fixed_connection_is_measured_at_the_terminals(qtbot, app, function, drawing):
    window = opened(qtbot, app, function, supply_connection="fixed")
    assert window.guide.test_object == drawing
    for index in range(1, window.count):
        window.go(index)
    window.bench.grab()
    assert {lead.terminal for lead in window.guide.leads} <= set(window.bench.anchors)


def test_stating_the_connection_at_the_first_station_changes_the_drawing(qtbot, app):
    with speaking("de"):
        window = opened(qtbot, app, "riso")
        assert window.guide.test_object == "cee_plug"
        window.form.fields["supply_connection"].setEditText("Schukostecker")
        window.form.edited.emit()
        assert window.guide.test_object == "schuko_plug"
        window.form.fields["supply_connection"].setEditText("fest angeschlossen")
        window.form.edited.emit()
        assert window.guide.test_object == "main_switch_on"
