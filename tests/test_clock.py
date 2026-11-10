# EasyMeasurement - tests/test_clock.py
# The instrument's clock: the driver, and setting it at the start of a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

import pytest

from easymeasurement.devices.base import DeviceError
from easymeasurement.devices.profitest_prime.driver import ProfitestPrimeDriver
from easymeasurement.devices.profitest_prime.transport import ForbiddenCommand, PrimeTransport
from easymeasurement.devices.simulator import SimulatedMeter

from .clock_helpers import HOUR, open_campaign
from .prime_helpers import FakeInstrument, empty_reply


class SettableInstrument(FakeInstrument):
    def write(self, data):
        command = data.decode().strip()
        if command.startswith("IDNXML:DATETIME:SET"):
            self.sent.append(command)
            self.incoming.put(empty_reply(command))
        else:
            super().write(data)


# Driver ----------------------------------------------------------------------


def test_clock_command_has_the_exact_format():
    instrument = SettableInstrument()
    with PrimeTransport(instrument) as transport:
        transport.set_clock(datetime(2026, 11, 6, 11, 41, 5))
    assert instrument.sent == ["IDNXML:DATETIME:SET 2026-11-06T11:41:05"]


@pytest.mark.parametrize(
    "command",
    ["IDNXML:DATETIME:SET", "IDNXML:DATETIME:SET 2026-11-06T11:41:05", "SYS:SET:TIME 11:41:05"],
)
def test_clock_cannot_be_set_through_the_general_command_path(command):
    instrument = SettableInstrument()
    with PrimeTransport(instrument) as transport, pytest.raises(ForbiddenCommand):
        transport.query(command)
    assert instrument.sent == []


def test_driver_sets_the_laptop_time_on_a_full_second():
    instrument = SettableInstrument()
    with ProfitestPrimeDriver(channel_factory=lambda: instrument) as driver:
        driver.sync_clock()
        sent_at = datetime.now()
    stamp = next(c for c in instrument.sent if "SET" in c).split()[1]
    assert abs(datetime.fromisoformat(stamp) - sent_at) < timedelta(seconds=2)


def test_clock_is_not_set_during_push():
    instrument = SettableInstrument()
    with ProfitestPrimeDriver(channel_factory=lambda: instrument) as driver:
        driver.subscribe_live(lambda reading: None)
        with pytest.raises(DeviceError, match="Push"):
            driver.sync_clock()
    assert not any("SET" in c for c in instrument.sent)


# Starting a campaign ---------------------------------------------------------


@pytest.mark.parametrize("skew", [5, -5, HOUR, -HOUR])
def test_clock_is_set_before_every_campaign(service, asset_id, plan, skew):
    meter = SimulatedMeter(clock_skew_s=skew)
    campaign = open_campaign(service, asset_id, plan, meter)
    assert abs(meter.read_clock() - datetime.now()) < timedelta(seconds=2)
    assert service.campaign(campaign)["clock_offset_s"] == 0


def test_setting_at_the_start_is_recorded(service, asset_id, plan):
    campaign = open_campaign(service, asset_id, plan, SimulatedMeter(clock_skew_s=HOUR))
    check = service.clock_checks(campaign)[0]
    assert check["kind"] == "set"
    assert check["offset_s"] == 0
    assert check["offset_before_s"] == pytest.approx(HOUR, abs=2)


def test_measurements_of_a_campaign_carry_no_offset(service, asset_id, plan):
    meter = SimulatedMeter(clock_skew_s=HOUR)
    campaign = open_campaign(service, asset_id, plan, meter)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)
    row = service.measurements(campaign)[0]
    assert row["clock_offset_s"] == 0
    assert row["device_time"] == row["local_time"]


def test_instrument_without_a_settable_clock_keeps_its_offset(service, asset_id, plan):
    meter = SimulatedMeter(clock_skew_s=HOUR, settable_clock=False)
    campaign = open_campaign(service, asset_id, plan, meter)
    assert service.campaign(campaign)["clock_offset_s"] == pytest.approx(HOUR, abs=2)
    assert service.clock_checks(campaign)[0]["kind"] == "measured"


def test_clock_that_ignores_the_command_stops_the_start(service, asset_id, plan, monkeypatch):
    """An instrument can answer a time command without carrying it out."""
    meter = SimulatedMeter(clock_skew_s=HOUR)
    monkeypatch.setattr(meter, "sync_clock", lambda: None)
    with pytest.raises(DeviceError, match="nicht stellen"):
        open_campaign(service, asset_id, plan, meter)
    assert service.campaigns() == []


def test_older_measurements_on_the_instrument_stay_out(service, asset_id, plan):
    meter = SimulatedMeter()
    meter.simulate_measurement("u", at=datetime.now() - timedelta(minutes=5))
    campaign = open_campaign(service, asset_id, plan, meter)
    assert service.collect(campaign, meter)["added"] == 0


def test_measurements_right_after_the_start_are_not_lost_to_an_old_offset(
    service, asset_id, plan
):
    meter = SimulatedMeter(clock_skew_s=HOUR)
    campaign = open_campaign(service, asset_id, plan, meter)
    meter.simulate_measurement("u")
    assert service.collect(campaign, meter)["added"] == 1


def test_reading_stamped_by_a_fast_clock_shows_up_as_open_not_as_a_result(
    service, asset_id, plan
):
    meter = SimulatedMeter(clock_skew_s=HOUR)
    meter.simulate_measurement("u")
    campaign = open_campaign(service, asset_id, plan, meter)
    assert service.collect(campaign, meter)["open"] == 1
