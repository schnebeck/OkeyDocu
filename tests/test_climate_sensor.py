# OkeyDocu - tests/test_climate_sensor.py
# A climate sensor: when it has settled, what it measures, where it is kept and how a report
# tells of it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.devices import LiveReading, find_instruments
from okeydocu.devices.climate import commands
from okeydocu.devices.climate.driver import measurement
from okeydocu.devices.climate.guides import hints
from okeydocu.devices.climate.known import KnownSensor, forget, known_sensors, remember
from okeydocu.devices.climate.protocols import Reading
from okeydocu.devices.climate.settling import Settling
from okeydocu.devices.climate.simulated import SimulatedClimate
from okeydocu.devices.instrument_check import NOTE, OK, run_checks
from okeydocu.l10n import speaking
from okeydocu.reporting.context import build_context

ADDRESS = "00:11:22:33:44:55"  # invented


def test_a_sensor_has_settled_after_a_minute_of_readings_within_a_tenth_of_a_degree():
    watch = Settling()
    for second in range(0, 61, 10):
        watch.add(second, 25.0 - second * 0.05)  # still cooling
    assert not watch.settled(60) and watch.left_s(60) > 0
    for second in range(70, 141, 10):
        watch.add(second, 21.43 + (second % 20) * 0.001)
    assert watch.settled(140) and watch.left_s(140) == 0


def test_a_reading_becomes_a_measurement_without_verdict():
    taken = measurement(Reading(21.31, 37.39, 3022, 100), datetime(2026, 3, 2, 9, 0, 0, 5))
    values = {value.key: value.quantity.raw for value in taken.results}
    assert taken.function == "ambient" and taken.verdict.value == "not_evaluated"
    assert values == {"t_air": "21.31\u00b0C", "rh": "37.4%", "u_battery": "3.022V"}
    assert taken.taken_at.microsecond == 0


def test_commands_for_the_display_and_the_name():
    assert commands.show(21.5, 5) == bytes.fromhex("22d70000000500" "05")
    assert commands.rename("Box 7") == b"\x01Box 7"
    assert commands.xiaomi_reading(bytes.fromhex("5b0826c20b")) == Reading(21.39, 38.0, 3010)


def test_only_texts_far_from_the_usual_conditions_give_hints():
    assert hints({"t_air": 21.0}) == [] and hints({"rh": 40.0}) == []
    assert len(hints({"t_air": -2.0})) == 2 and len(hints({"t_air": 33.0})) == 1


def test_enrolled_sensors_are_kept_in_the_data_folder_and_offered_beside(tmp_path):
    remember(KnownSensor(ADDRESS, "Box 7", "bthome", "Example", "T1"), tmp_path)
    remember(KnownSensor(ADDRESS, "Box 8", "bthome", "Example", "T1"), tmp_path)
    assert [sensor.name for sensor in known_sensors(tmp_path)] == ["Box 8"]
    forget(ADDRESS, tmp_path)
    assert known_sensors(tmp_path) == []


def test_a_sensor_is_never_a_campaigns_own_source(monkeypatch, tmp_path):
    monkeypatch.setenv("OKEYDOCU_DATA", str(tmp_path))
    remember(KnownSensor(ADDRESS, "Box 7", "bthome"))
    assert all(found.key != "climate" for found in find_instruments())
    assert any(found.port == ADDRESS for found in find_instruments(companions=True))


def test_the_simulated_sensor_comes_out_of_a_warm_pocket(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr("okeydocu.devices.climate.simulated.time.monotonic", lambda: clock[0])
    sensor = SimulatedClimate()
    sensor.open()
    first, _, left = sensor.latest()
    assert first.temperature > sensor.air + 5 and left > 0
    for _ in range(40):
        clock[0] += 1.0
        reading, _, left = sensor.latest()
    assert left == 0 and abs(reading.temperature - sensor.air) < 0.1
    assert sensor.take().function == "ambient"


@pytest.fixture
def campaign(service):
    customer = service.db.add_customer("Example Works")
    machine = service.db.add_asset(customer, "machine", "Press")
    return service.create(machine, "Inspection", "Inspector")


def test_the_report_names_the_conditions_and_the_sensor_as_not_calibrated(service, campaign):
    sensor = SimulatedClimate("sim-7")
    identity = sensor.identify()
    slot = service.book(campaign, "climate-simulator", identity, beside=True)
    taken = measurement(Reading(23.46, 29.2, 2990), datetime(2026, 3, 2, 9, 30))
    service.receive(campaign, LiveReading(taken, datetime(2026, 3, 2, 9, 30)), slot=slot)
    with speaking("de"):
        context = build_context(service, campaign)
    assert context["campaign"]["conditions"].startswith("23,5 \u00b0C, 29 % r. F., gemessen")
    assert identity.model in context["campaign"]["conditions"]
    listed = context["devices"]
    assert [device["calibration"] for device in listed] == ["nicht kalibriert, Werte zur Information"]


def test_a_sensor_is_tested_for_who_it_is_and_a_reading_and_said_to_be_uncalibrated():
    run = run_checks(SimulatedClimate("sim-7"), datetime(2026, 3, 2).date(), calibrated=False)
    states = {check.key: check.state for check in run.checks}
    assert states == {"identity": OK, "calibration": NOTE, "reading": OK} and run.ready
