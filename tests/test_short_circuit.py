# OkeyDocu - tests/test_short_circuit.py
# A short-circuit current measured at a machine, held against the rating it states.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

from okeydocu.campaign.short_circuit import above_rating, rating_of
from okeydocu.devices.base import LiveReading
from okeydocu.devices.guide import MEASURE
from okeydocu.l10n import speaking
from okeydocu.model import MeterMeasurement, Quantity, ResultValue, Verdict
from okeydocu.store.kinds import shipped_kinds
from okeydocu.ui.measuring_window import MeasuringWindow

NOW = datetime(2026, 3, 2, 9, 0)


def loop(current: str) -> MeterMeasurement:
    results = (ResultValue("zloop", "Z", Quantity.parse("0.02Ohm")),
               ResultValue("ik", "IK", Quantity.parse(current)))
    return MeterMeasurement("x", "zloop", NOW, Verdict.NOT_EVALUATED, results=results)


def test_a_rating_reads_in_kiloamperes_or_amperes():
    assert rating_of("10 kA") == 10_000 and rating_of("6,5kA") == 6_500
    assert rating_of("800 A") == 800
    assert rating_of("") is None and rating_of("400 V") is None and rating_of("0 kA") is None


def test_only_a_current_above_the_rating_is_named():
    assert [(raw, rating) for _, raw, rating in above_rating(loop("11.5kA"), "10 kA")] == [
        ("11.5kA", 10)]
    assert above_rating(loop("9.8kA"), "10 kA") == []
    assert above_rating(loop("10kA"), "10 kA") == []  # at the rating is not above it
    assert above_rating(loop("11.5kA"), "") == []  # nothing stated, nothing judged


def test_the_machine_states_its_rating_and_the_installation_its_supply():
    units = {kind.key: {feature.key: feature.unit for feature in kind.features}
             for kind in shipped_kinds()}
    assert units["machine"]["short_circuit_rating"] == "kA"
    assert units["installation"]["supply_impedance"] == "Ω"
    assert units["installation"]["supply_short_circuit_current"] == "kA"
    assert "supply_short_circuit_current" not in units["machine"]  # it belongs to the place


def test_the_measure_station_names_a_current_above_the_rating(qtbot, app):
    customer = app.db.add_customer("Example Works")
    machine = app.db.add_asset(customer, "machine", "Press")
    app.db.set_asset_features(machine, {"short_circuit_rating": "10"})
    campaign = app.service.create(machine, "Inspection", "Inspector")
    with speaking("en"):
        window = MeasuringWindow(app, campaign, "profitest-prime", "zloop", machine)
        qtbot.addWidget(window)
        window.go(next(i for i, s in enumerate(window.guide.flow) if s.kind == MEASURE))
        window.show_reading(LiveReading(loop("11.5kA"), NOW))
        above = window.step_text.text()
        window.show_reading(LiveReading(loop("3.2kA"), NOW))
        below = window.step_text.text()
    assert "IK 11.5kA: above the short-circuit current rating of 10 kA stated here" in above
    assert "short-circuit current rating" not in below
