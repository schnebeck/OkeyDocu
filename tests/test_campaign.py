# EasyMeasurement - tests/test_campaign.py
# Campaign flow: baseline, clock offset and assignment to steps.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

import pytest

from easymeasurement.campaign.assignment import StepWindow, assign
from easymeasurement.devices.simulator import SimulatedMeter

from .campaign_helpers import T0, start, step_of


def test_old_measurements_on_the_device_are_never_collected(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    meter.simulate_measurement("riso", at=T0 - timedelta(days=30))
    campaign = service.start(asset_id, plan, "Prüfung", "Prüfer", "simulator", meter)
    assert service.collect(campaign, meter)["added"] == 0


def test_collect_is_repeatable(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    step = step_of(service, campaign, "rlo")
    service.confirm_setup(step["id"], now=T0)
    meter.simulate_measurement("rlo", at=T0 + timedelta(seconds=30))
    assert service.collect(campaign, meter) == {"added": 1, "assigned": 1, "open": 0}
    assert service.collect(campaign, meter)["added"] == 0


def test_any_number_of_measurements_land_on_the_confirmed_step(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    step = step_of(service, campaign, "riso")
    service.confirm_setup(step["id"], now=T0)
    for n in range(5):
        meter.simulate_measurement("riso", at=T0 + timedelta(seconds=20 * n))
    service.collect(campaign, meter)
    assert len(service.measurements(campaign, step["id"])) == 5


def test_large_clock_skew_is_corrected(service, asset_id, plan):
    skew = 49 * 60 + 7
    meter = SimulatedMeter(clock_skew_s=skew, seed=1, settable_clock=False)
    campaign = start(service, asset_id, plan, meter)
    assert service.campaign(campaign)["clock_offset_s"] == pytest.approx(skew, abs=1.5)
    step = step_of(service, campaign, "rlo")
    now = datetime.now()
    service.confirm_setup(step["id"], now=now)
    meter.simulate_measurement("rlo", at=now + timedelta(seconds=30))
    assert service.collect(campaign, meter)["assigned"] == 1


def test_wrong_function_stays_open_instead_of_being_guessed(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    service.confirm_setup(step_of(service, campaign, "rlo")["id"], now=T0)
    meter.simulate_measurement("riso", at=T0 + timedelta(seconds=30))
    assert service.collect(campaign, meter) == {"added": 1, "assigned": 0, "open": 1}
    row = service.open_measurements(campaign)[0]
    assert row["issue"] == "function_mismatch"


def test_measurement_between_steps_stays_open(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    step = step_of(service, campaign, "rlo")
    service.confirm_setup(step["id"], now=T0)
    service.finish_step(step["id"], now=T0 + timedelta(minutes=1))
    meter.simulate_measurement("rlo", at=T0 + timedelta(minutes=5))
    service.collect(campaign, meter)
    assert service.open_measurements(campaign)[0]["issue"] == "outside_window"


def test_returning_to_a_step_opens_a_second_window(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    rlo = step_of(service, campaign, "rlo")
    riso = step_of(service, campaign, "riso")
    service.confirm_setup(rlo["id"], now=T0)
    service.confirm_setup(riso["id"], now=T0 + timedelta(minutes=5))
    service.confirm_setup(rlo["id"], now=T0 + timedelta(minutes=10))
    meter.simulate_measurement("rlo", at=T0 + timedelta(minutes=1))
    meter.simulate_measurement("riso", at=T0 + timedelta(minutes=6))
    meter.simulate_measurement("rlo", at=T0 + timedelta(minutes=11))
    assert service.collect(campaign, meter)["assigned"] == 3
    assert len(service.measurements(campaign, rlo["id"])) == 2


def test_manual_assignment_resolves_an_open_measurement(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    meter.simulate_measurement("rlo", at=T0)
    service.collect(campaign, meter)
    row = service.open_measurements(campaign)[0]
    service.assign_manually(row["id"], step_of(service, campaign, "rlo")["id"])
    assert service.open_measurements(campaign) == []


def test_window_edge_slack():
    window = StepWindow(1, T0, T0 + timedelta(minutes=1), frozenset({"rlo"}))
    assert assign(T0 - timedelta(seconds=2), "rlo", [window]).step_id == 1
    assert assign(T0 - timedelta(seconds=3), "rlo", [window]).step_id is None


def test_overdue_calibration_is_recognised():
    identity = SimulatedMeter(overdue=True).identify()
    assert identity.calibration_overdue(datetime.now().date())


def test_simulator_can_fail_and_marks_it():
    meter = SimulatedMeter(seed=4, failure_rate=1.0)
    measurement = meter.simulate_measurement("riso", at=T0)
    assert measurement.verdict.value == "failed"
    assert measurement.result("riso").quantity.base_value < 1e6
    assert measurement.result("riso").verdict.value == "failed"
    assert measurement.result("u_iso").verdict.value == "not_evaluated"


def test_plan_carries_the_instrument_into_the_stored_step(service, asset_id, plan):
    campaign = start(service, asset_id, plan, SimulatedMeter(seed=1))
    wiring = service.plan_step(service.steps(campaign)[0]).wiring
    assert wiring.sockets == ("1(L)", "2(N)", "3(PE)")
    assert wiring.instrument == "PROFITEST PRIME"
