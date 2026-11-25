# OkeyDocu - tests/test_conductor_limit.py
# The limit proposed for the protective conductor of a supply cable.
# l10n: de
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.campaign.conductor_limit import conductor_limit
from okeydocu.devices.guide import CONFIGURE
from okeydocu.l10n import speaking
from okeydocu.ui.limit_text import limit_text
from okeydocu.ui.measuring_window import MeasuringWindow


def stating(**features):
    return lambda key: features.get(key, "")


def test_a_thick_cable_on_a_plug_is_judged_by_its_conductor_and_the_contacts():
    found = conductor_limit(stating(cable_length="5 m", cross_section="2,5 mm²",
                                    supply_connection="CEE plug"))
    assert found.conductor == pytest.approx(0.0378)
    assert found.value == pytest.approx(0.1378)
    assert found.binding and not found.by_length


@pytest.mark.parametrize("length, limit", [("3", 0.3), ("5", 0.3), ("5,1", 0.4), ("12,5", 0.4),
                                           ("13", 0.5), ("80", 1.0)])
def test_a_cord_up_to_1_5_mm2_on_a_plug_has_its_limit_by_its_length(length, limit):
    found = conductor_limit(stating(cable_length=length, cross_section="1.5",
                                    supply_connection="Schuko plug"))
    assert found.value == pytest.approx(limit) and found.by_length and found.binding


@pytest.mark.parametrize("connection", ["fixed", ""])
def test_a_fixed_connection_has_no_limit_only_what_to_expect(connection):
    found = conductor_limit(stating(cable_length="20", cross_section="1,5",
                                    supply_connection=connection))
    assert not found.binding and not found.by_length
    assert found.value == pytest.approx(0.0189 * 20 / 1.5 + 0.1)


@pytest.mark.parametrize("features", [
    {"cable_length": "5"}, {"cross_section": "2,5"}, {},
    {"cable_length": "5", "cross_section": "16", "conductor_material": "Al"},
    {"cable_length": "0", "cross_section": "2,5"},
])
def test_nothing_is_proposed_from_what_the_element_does_not_state(features):
    assert conductor_limit(stating(**features)) is None


def test_the_proposal_shows_its_reckoning():
    stated = stating(cable_length="5 m", cross_section="2,5 mm²", supply_connection="CEE plug")
    with speaking("de"):
        text = limit_text("rlo", stated, "Bandsäge")
        assert "Vorgeschlagener Grenzwert für Bandsäge: <b>0,14 Ω</b>" in text
        assert "5 m Kupfer mit 2,5 mm²: 0,04 Ω für den Leiter und 0,10 Ω für die Übergänge." in text
        assert "EN 50678 und EN 50699, 5.3" in text
        fixed = limit_text("rlo_25a", stating(cable_length="5", cross_section="2,5"), "Presse")
        assert "Kein fester Grenzwert für Presse; zu erwarten: bis <b>0,14 Ω</b>" in fixed
        assert "EN 60204-1, 18.2.2" in fixed


def test_only_the_protective_conductor_gets_this_proposal():
    stated = stating(cable_length="5", cross_section="2,5", supply_connection="CEE plug")
    assert limit_text("riso", stated, "Presse") == ""
    assert limit_text("rlo", stating(), "Presse") == ""


def test_mode_and_limits_propose_the_limit_from_what_the_machine_states(qtbot, app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    app.db.set_asset_features(machine, {"supply_cable": "H07RN-F", "cable_length": "5",
                                        "cross_section": "2,5",
                                        "supply_connection": "CEE plug"})
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, "profitest-prime", "rlo", machine)
        qtbot.addWidget(window)
        window.go(next(i for i, s in enumerate(window.guide.flow) if s.kind == CONFIGURE))
        text = window.step_text.text()
    assert "Vorgeschlagener Grenzwert für Presse: <b>0,14 Ω</b>" in text
    assert "5 m Kupfer mit 2,5 mm²" in text
