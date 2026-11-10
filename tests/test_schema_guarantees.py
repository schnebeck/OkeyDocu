# EasyMeasurement - tests/test_schema_guarantees.py
# What the schema guarantees: logging, origin of readings, once per device, stored keys.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import sqlite3

import pytest

from easymeasurement.campaign.plan import load_plans
from easymeasurement.campaign.service import CampaignService
from easymeasurement.devices.simulator import SimulatedMeter
from easymeasurement.model import Quantity, ResultValue
from easymeasurement.store import Database, SchemaMismatch
from easymeasurement.store.database import SCHEMA_VERSION, DuplicateMeasurement
from easymeasurement.store.search import MeasurementFilter, search_measurements


def test_file_database_uses_write_ahead_logging(tmp_path):
    db = Database(tmp_path / "data.sqlite")
    assert db.one("PRAGMA journal_mode")[0] == "wal"
    assert db.one("PRAGMA synchronous")[0] == 2


@pytest.fixture
def setup(tmp_path):
    db = Database(tmp_path / "data.sqlite")
    customer = db.add_customer("Muster AG")
    asset = db.add_asset(customer, "installation", "Halle 1")
    return CampaignService(db, tmp_path / "archive"), asset


def _open(service, asset, meter):
    plan = load_plans()[0]
    return service.start(asset, plan, "Prüfung", "Prüfer", "simulator", meter)


def test_measurement_records_where_it_came_from(setup):
    service, asset = setup
    meter = SimulatedMeter(seed=1)
    campaign = _open(service, asset, meter)
    meter.simulate_measurement("u")
    service.collect(campaign, meter)
    row = service.measurements(campaign)[0]
    assert row["device_serial"] == "SIM-0001"
    assert row["firmware"] == "1.0"
    assert row["received_at"][-6] in "+-"  # with time zone


def test_device_measurement_cannot_enter_a_second_campaign(setup):
    service, asset = setup
    meter = SimulatedMeter(seed=1)
    first = _open(service, asset, meter)
    meter.simulate_measurement("u")
    service.collect(first, meter)
    uid = service.measurements(first)[0]["device_uid"]

    other = SimulatedMeter(seed=2)
    second = _open(service, asset, other)
    with pytest.raises(DuplicateMeasurement):
        service.db.execute(
            "INSERT INTO measurements (campaign_id, device_uid, source, function, local_time,"
            " verdict) VALUES (?, ?, 'device:simulator', 'u', '2026-01-01T09:00:00', 'passed')",
            second, uid,
        )


def test_collect_skips_what_another_campaign_already_holds(setup):
    service, asset = setup
    meter = SimulatedMeter(seed=1)
    first = _open(service, asset, meter)
    meter.simulate_measurement("u")
    service.collect(first, meter)

    other = SimulatedMeter(seed=1)  # same seed, so the same GUID
    second = _open(service, asset, other)
    other.simulate_measurement("u")
    assert service.collect(second, other)["added"] == 0


def test_giga_values_are_found_by_a_filter_in_ohm(setup):
    service, asset = setup
    campaign = service.create(asset, "Prüfung", "Prüfer", None)
    service.add_measurement(
        campaign, "riso", [ResultValue("riso", "RISO", Quantity.parse(">1.20G\u2126"))]
    )
    found = search_measurements(
        service.db, MeasurementFilter(value_key="riso", value_min=1e6, value_unit="Ω")
    )
    assert len(found) == 1


@pytest.mark.parametrize("offset", [-1, 1])
def test_a_database_of_another_version_is_refused_and_left_alone(tmp_path, offset):
    path = tmp_path / "other.sqlite"
    Database(path).close()
    connection = sqlite3.connect(path)
    connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION + offset}")
    connection.commit()
    connection.close()
    before = path.read_bytes()
    with pytest.raises(SchemaMismatch, match="externen Werkzeug"):
        Database(path)
    assert path.read_bytes() == before
    assert [file.name for file in tmp_path.iterdir()] == ["other.sqlite"]


def test_a_new_database_gets_the_current_version(tmp_path):
    db = Database(tmp_path / "new.sqlite")
    assert db.one("PRAGMA user_version")[0] == SCHEMA_VERSION
    db.close()
