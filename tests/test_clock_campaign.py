# EasyMeasurement - tests/test_clock_campaign.py
# The clock during a campaign: drift, offsets by hand, the report and the status.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

import pytest

from easymeasurement.campaign.service import CLOCK_TOLERANCE_S, ClockState, clock_needs_setting
from easymeasurement.devices.base import DeviceError
from easymeasurement.devices.simulator import SimulatedMeter
from easymeasurement.reporting.context import build_context
from easymeasurement.store import CampaignClosed

from .clock_helpers import HOUR, open_campaign


def drifted_campaign(service, asset_id, plan, seconds=HOUR):
    """A campaign during which the clock has moved away from the laptop."""
    meter = SimulatedMeter()
    campaign = open_campaign(service, asset_id, plan, meter)
    meter._skew = timedelta(seconds=seconds)
    service.check_clock(campaign, meter)
    return campaign, meter


def local_times(service, campaign):
    return [datetime.fromisoformat(m["local_time"]) for m in service.measurements(campaign)]


# During a campaign -----------------------------------------------------------


def test_small_drift_is_not_worth_a_question():
    meter = SimulatedMeter()
    assert clock_needs_setting(CLOCK_TOLERANCE_S, meter)
    assert clock_needs_setting(-CLOCK_TOLERANCE_S, meter)
    assert not clock_needs_setting(CLOCK_TOLERANCE_S - 1, meter)


def test_setting_the_clock_mid_campaign_falsifies_no_time(service, asset_id, plan):
    campaign, meter = drifted_campaign(service, asset_id, plan)
    meter.simulate_measurement("u")  # stored on the instrument, stamped by the drifted clock
    service.sync_device_clock(campaign, meter)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)

    now = datetime.now()
    assert len(local_times(service, campaign)) == 2
    for moment in local_times(service, campaign):
        assert abs(moment - now) < timedelta(seconds=10)


def test_each_measurement_keeps_the_offset_it_was_converted_with(service, asset_id, plan):
    campaign, meter = drifted_campaign(service, asset_id, plan)
    meter.simulate_measurement("u")
    service.sync_device_clock(campaign, meter)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)
    first, second = sorted(
        service.measurements(campaign), key=lambda row: row["clock_offset_s"], reverse=True
    )
    assert first["clock_offset_s"] == pytest.approx(HOUR, abs=2)
    assert second["clock_offset_s"] == 0


def test_clock_stays_untouched_if_stored_measurements_cannot_be_fetched(
    service, asset_id, plan, monkeypatch
):
    campaign, meter = drifted_campaign(service, asset_id, plan)

    def blocked():
        raise DeviceError("Fehler 402")

    monkeypatch.setattr(meter, "read_measurements", blocked)
    with pytest.raises(DeviceError):
        service.sync_device_clock(campaign, meter)
    assert meter.read_clock() - datetime.now() > timedelta(seconds=HOUR - 5)


def test_a_new_check_is_used_for_measurements_after_it(service, asset_id, plan):
    campaign, meter = drifted_campaign(service, asset_id, plan, 160)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)
    assert abs(local_times(service, campaign)[0] - datetime.now()) < timedelta(seconds=10)


def test_clock_history_of_a_closed_campaign_is_frozen(service, asset_id, plan):
    campaign = open_campaign(service, asset_id, plan, SimulatedMeter())
    service.db.execute("UPDATE campaigns SET status='closed' WHERE id=?", campaign)
    with pytest.raises(CampaignClosed):
        service.db.execute("DELETE FROM clock_checks WHERE campaign_id=?", campaign)


# By hand ---------------------------------------------------------------------


def test_offset_by_hand_recalculates_times_and_keeps_the_device_time(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = open_campaign(service, asset_id, plan, meter)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)
    row = service.measurements(campaign)[0]
    service.correct_clock_offset(campaign, -600)

    changed = service.measurements(campaign)[0]
    device_time = datetime.fromisoformat(row["device_time"])
    assert changed["device_time"] == row["device_time"]
    assert datetime.fromisoformat(changed["local_time"]) == device_time + timedelta(seconds=600)
    assert changed["clock_offset_s"] == -600
    assert service.clock_checks(campaign)[-1]["kind"] == "manual"


def test_offset_by_hand_leaves_a_personal_assignment_alone(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = open_campaign(service, asset_id, plan, meter)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)
    row = service.measurements(campaign)[0]
    step = service.steps(campaign)[0]["id"]
    service.assign_manually(row["id"], step)
    service.correct_clock_offset(campaign, 500)
    assert service.measurements(campaign, step)[0]["assignment"] == "manual"


def test_offset_by_hand_is_refused_after_setting_during_the_campaign(service, asset_id, plan):
    campaign, meter = drifted_campaign(service, asset_id, plan)
    service.sync_device_clock(campaign, meter)
    with pytest.raises(DeviceError, match="gestellt"):
        service.correct_clock_offset(campaign, 10)


# Report ----------------------------------------------------------------------


def test_report_says_the_clock_was_set_and_nothing_about_an_offset(service, asset_id, plan):
    campaign = open_campaign(service, asset_id, plan, SimulatedMeter(clock_skew_s=120))
    summary = build_context(service, campaign)["campaign"]["clock_summary"]
    assert "gestellt" in summary
    assert "korrigiert" not in summary


def test_report_names_an_offset_that_had_to_stay(service, asset_id, plan):
    meter = SimulatedMeter(clock_skew_s=120, settable_clock=False)
    campaign = open_campaign(service, asset_id, plan, meter)
    summary = build_context(service, campaign)["campaign"]["clock_summary"]
    assert "korrigiert" in summary


def test_report_shows_a_second_setting_too(service, asset_id, plan):
    campaign, meter = drifted_campaign(service, asset_id, plan)
    service.sync_device_clock(campaign, meter)
    summary = build_context(service, campaign)["campaign"]["clock_summary"]
    assert summary.count("gestellt") == 2


# Status ----------------------------------------------------------------------


def test_status_after_setting_at_the_start(service, asset_id, plan):
    campaign = open_campaign(service, asset_id, plan, SimulatedMeter(clock_skew_s=HOUR))
    status = service.clock_status(campaign)
    assert status.state is ClockState.SYNCED
    assert "gestellt" in status.text


def test_status_shows_a_clock_that_drifted_away(service, asset_id, plan):
    campaign, _ = drifted_campaign(service, asset_id, plan, 120)
    status = service.clock_status(campaign)
    assert status.state is ClockState.OFFSET
    assert "+120" in status.text or "+119" in status.text


def test_status_shows_a_clock_that_cannot_be_set(service, asset_id, plan):
    meter = SimulatedMeter(clock_skew_s=HOUR, settable_clock=False)
    campaign = open_campaign(service, asset_id, plan, meter)
    assert service.clock_status(campaign).state is ClockState.OFFSET


def test_small_deviation_counts_as_in_step(service, asset_id, plan):
    campaign, _ = drifted_campaign(service, asset_id, plan, 1)
    assert service.clock_status(campaign).state is ClockState.SYNCED


def test_campaign_without_an_instrument_has_no_clock_status(service, asset_id):
    campaign = service.create(asset_id, "Prüfung", "Prüfer")
    assert service.clock_status(campaign) is None


def test_old_campaign_without_checks_is_unknown(service, asset_id, plan):
    campaign = open_campaign(service, asset_id, plan, SimulatedMeter())
    service.db.execute("DELETE FROM clock_checks WHERE campaign_id=?", campaign)
    assert service.clock_status(campaign).state is ClockState.UNKNOWN
