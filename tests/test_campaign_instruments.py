# OkeyDocu - tests/test_campaign_instruments.py
# Booking instruments into a campaign and out again.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.instruments import InstrumentInUse
from okeydocu.campaign.records import MANUAL
from okeydocu.campaign.seal import content
from okeydocu.devices.base import LiveReading
from okeydocu.model import DeviceIdentity, MeterMeasurement, Quantity, ResultValue, Verdict

METER = DeviceIdentity(manufacturer="Example Meters", model="Tester 1", serial_no="T-0001")
SENSOR = DeviceIdentity(manufacturer="Example Sensors", model="Climate 2", serial_no="C-0002")


def reading(uid: str, function: str = "u") -> LiveReading:
    value = ResultValue("u", "U", Quantity.parse("230V"), Verdict.NOT_EVALUATED, "", "")
    moment = datetime(2026, 3, 2, 9, 0)
    return LiveReading(MeterMeasurement(uid, function, moment, Verdict.PASSED, results=(value,)),
                       moment)


@pytest.fixture
def campaign(service):
    customer = service.db.add_customer("Example Works")
    machine = service.db.add_asset(customer, "machine", "Press")
    return service.create(machine, "Inspection", "Inspector")


def test_a_campaign_without_instrument_takes_the_first_one_booked_as_its_own(service, campaign):
    assert service.instruments(campaign) == []
    assert service.book(campaign, "meter", METER, 4.0) == 0
    second = service.book(campaign, "sensor", SENSOR)
    assert second > 0
    kinds = [(booked.slot, booked.driver, booked.identity.serial_no)
             for booked in service.instruments(campaign)]
    assert kinds == [(0, "meter", "T-0001"), (second, "sensor", "C-0002")]
    assert service.campaign(campaign)["clock_offset_s"] == 4.0


def test_a_reading_names_the_instrument_it_came_from(service, campaign):
    service.book(campaign, "meter", METER, 10.0)
    sensor = service.book(campaign, "sensor", SENSOR)
    service.receive(campaign, reading("a"))
    service.receive(campaign, reading("b"), slot=sensor)
    rows = {row["device_uid"]: row for row in service.measurements(campaign)}
    assert (rows["a"]["source"], rows["a"]["device_serial"]) == ("device:meter", "T-0001")
    assert (rows["b"]["source"], rows["b"]["device_serial"]) == ("device:sensor", "C-0002")
    assert rows["a"]["local_time"] < rows["b"]["local_time"]  # only the meter's clock is off


def test_an_instrument_leaves_only_while_it_has_not_measured(service, campaign):
    service.book(campaign, "meter", METER)
    sensor = service.book(campaign, "sensor", SENSOR)
    service.receive(campaign, reading("a"), slot=sensor)
    with pytest.raises(InstrumentInUse):
        service.release(campaign, sensor)
    service.release(campaign, 0)  # the meter has not measured
    assert [(b.slot, b.driver) for b in service.instruments(campaign)] == [(sensor, "sensor")]
    assert service.campaign(campaign)["driver"] == MANUAL


def test_an_instrument_beside_never_becomes_the_campaigns_own(service, campaign):
    sensor = service.book(campaign, "sensor", SENSOR, beside=True)
    assert sensor > 0 and service.campaign(campaign)["driver"] == MANUAL
    service.release(campaign, sensor)
    assert service.instruments(campaign) == []


def test_the_seal_takes_further_instruments_and_reads_as_before_without_them(service, campaign):
    service.book(campaign, "meter", METER)
    alone = content(service.db, campaign, "2026-03-02T10:00:00")
    assert b'"instruments"' not in alone
    service.book(campaign, "sensor", SENSOR)
    assert b"C-0002" in content(service.db, campaign, "2026-03-02T10:00:00")
