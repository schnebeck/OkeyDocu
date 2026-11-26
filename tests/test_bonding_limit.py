# OkeyDocu - tests/test_bonding_limit.py
# The limit of supplementary protective bonding from the protective device the element states.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.campaign.bonding_limit import bonding_limit, tripping_multiple
from okeydocu.devices.guide import CONFIGURE
from okeydocu.l10n import speaking
from okeydocu.store.choice_lists import shipped_choice_lists
from okeydocu.ui.limit_text import limit_text
from okeydocu.ui.measuring_window import MeasuringWindow

CURVES = {"B": "breaker 3 5", "C": "breaker 5 10", "K": "breaker 8 12 1.05 1.2", "gG": ""}


def stating(**features):
    return lambda key: features.get(key, "")


def curve_of(characteristic):
    return CURVES.get(characteristic, "")


@pytest.mark.parametrize("characteristic, rated, current, limit", [
    ("B", "16 A", 80, 0.625), ("C", "16", 160, 0.3125), ("K", "10 A", 120, 50 / 120)])
def test_the_limit_is_fifty_volts_over_the_current_that_trips_the_breaker(
        characteristic, rated, current, limit):
    found = bonding_limit(stating(characteristic=characteristic, rated_current=rated), curve_of)
    assert found.current == pytest.approx(current) and found.value == pytest.approx(limit)


@pytest.mark.parametrize("features", [
    {"characteristic": "C"}, {"rated_current": "16"}, {},
    {"characteristic": "gG", "rated_current": "16"},  # a fuse has no instantaneous range
    {"characteristic": "RCD-S", "rated_current": "40"},  # not a characteristic of a breaker
])
def test_nothing_is_proposed_without_a_breaker_and_its_rating(features):
    assert bonding_limit(stating(**features), curve_of) is None


def test_a_curve_names_its_instantaneous_range():
    assert tripping_multiple("breaker 5 10") == 10 and tripping_multiple("breaker 2 3 1.05 1.2") == 3
    assert tripping_multiple("") is None and tripping_multiple("fuse 5") is None


def test_the_shipped_characteristics_of_breakers_give_a_multiple():
    shipped = {known.key: known for known in shipped_choice_lists()}["characteristic"]
    multiples = {entry.value: tripping_multiple(entry.curve) for entry in shipped.values}
    assert multiples["B"] == 5 and multiples["C"] == 10 and multiples["D"] == 20


def test_the_proposal_shows_its_reckoning_beside_what_the_conductor_lets_expect():
    stated = stating(cable_length="20", cross_section="2,5", characteristic="C",
                     rated_current="16 A")
    with speaking("de"):
        text = limit_text("rlo", stated, "Presse", curve_of)
        assert "Mit zusätzlichem Schutzpotentialausgleich: höchstens <b>0,31 Ω</b>" in text
        assert "C 16 A löst spätestens bei 160 A aus: 50 V / 160 A." in text
        assert "zu erwarten: bis <b>0,25 Ω</b>" in text  # the conductor, as before
        assert "Schutzpotentialausgleich" not in limit_text("rlo", stated, "Presse")
        assert limit_text("riso", stated, "Presse", curve_of) == ""


def test_mode_and_limits_tell_the_limit_from_the_breaker_the_machine_states(qtbot, app):
    customer = app.db.add_customer("Example Works")
    machine = app.db.add_asset(customer, "machine", "Press")
    app.db.set_asset_features(machine, {"characteristic": "C", "rated_current": "16"})
    campaign = app.service.create(machine, "Inspection", "Inspector")
    with speaking("en"):
        window = MeasuringWindow(app, campaign, "profitest-prime", "rlo", machine)
        qtbot.addWidget(window)
        window.go(next(i for i, s in enumerate(window.guide.flow) if s.kind == CONFIGURE))
        text = window.step_text.text()
    assert "With supplementary protective bonding: at most <b>0.31 Ω</b>" in text
    assert "C 16 A trips at 160 A at the latest: 50 V / 160 A." in text
