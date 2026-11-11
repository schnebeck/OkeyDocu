# EasyMeasurement - tests/test_measurement_rules.py
# Value, unit and time are final. Changes of substance leave a trace, text fixes do not.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import sqlite3

import pytest

from easymeasurement.devices.simulator import SimulatedMeter
from easymeasurement.model import Quantity, ResultValue
from easymeasurement.reporting.context import build_context as report_context
from easymeasurement.reporting.measurement_words import marks as _marks
from easymeasurement.store import ReadingIsFinal


@pytest.fixture
def stored(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = service.start(asset_id, plan, "P", "T", "simulator", meter)
    meter.simulate_measurement("riso")
    service.collect(campaign, meter)
    row = service.measurements(campaign)[0]
    return campaign, row, service.values(row["id"]), meter


# What stands -----------------------------------------------------------------


@pytest.mark.parametrize(
    "column, value",
    [("raw", "1MΩ"), ("base_value", 1.0), ("base_unit", "V"), ("qualifier", ">"), ("kind", "text")],
)
def test_database_refuses_to_change_a_reading(service, stored, column, value):
    with pytest.raises(ReadingIsFinal):
        service.db.execute(f"UPDATE measured_values SET {column}=?", value)


def test_database_refuses_to_change_the_device_time(service, stored):
    with pytest.raises(ReadingIsFinal):
        service.db.execute("UPDATE measurements SET device_time='2020-01-01T00:00:00'")


@pytest.mark.parametrize("field", ["local_time", "device_time", "source", "raw_data"])
def test_service_refuses_fields_that_stand(service, stored, field):
    _, row, _, _ = stored
    with pytest.raises(ReadingIsFinal):
        service.edit_measurement(row["id"], {field: "x"})


@pytest.mark.parametrize("field", ["raw", "base_value", "base_unit"])
def test_service_refuses_value_fields_that_stand(service, stored, field):
    _, row, values, _ = stored
    with pytest.raises(ReadingIsFinal):
        service.edit_measurement(row["id"], value_changes={values[0]["id"]: {field: "x"}})


def test_a_refused_change_changes_nothing_at_all(service, stored):
    _, row, _, _ = stored
    with pytest.raises(ReadingIsFinal):
        service.edit_measurement(row["id"], {"comment": "neu", "local_time": "x"})
    assert service.measurements(stored[0])[0]["comment"] == row["comment"]
    assert service.measurement_changes(row["id"]) == []


def test_correcting_the_clock_offset_still_works(service, stored):
    campaign, row, _, _ = stored
    service.correct_clock_offset(campaign, 60)
    assert service.measurements(campaign)[0]["device_time"] == row["device_time"]


# What can be overwritten -----------------------------------------------------


def test_fields_around_a_reading_can_be_overwritten(service, stored):
    campaign, row, _, _ = stored
    service.edit_measurement(row["id"], {
        "location": "Schrank / F1", "comment": "Nachgetragen", "operator": "B. Prüfer",
        "function": "riso_ramp", "verdict": "failed",
    })
    changed = service.measurements(campaign)[0]
    assert changed["location"] == "Schrank / F1"
    assert changed["comment"] == "Nachgetragen"
    assert changed["operator"] == "B. Prüfer"
    assert changed["function"] == "riso_ramp"
    assert changed["verdict"] == "failed"


def test_limit_label_and_verdict_of_a_value_can_be_overwritten(service, stored):
    _, row, values, _ = stored
    service.edit_measurement(row["id"], value_changes={values[0]["id"]: {
        "lower_limit": ">2.00MΩ", "label": "RISO L1-PE", "verdict": "failed",
    }})
    value = service.values(row["id"])[0]
    assert value["lower_limit"] == ">2.00MΩ"
    assert value["label"] == "RISO L1-PE"
    assert value["verdict"] == "failed"
    assert value["raw"] == values[0]["raw"]


def test_change_of_substance_leaves_old_and_new_value(service, stored):
    _, row, _, _ = stored
    service.edit_measurement(row["id"], {"verdict": "failed"})
    entry = service.measurement_changes(row["id"])[0]
    assert (entry["action"], entry["field"]) == ("edit", "verdict")
    assert (entry["old_value"], entry["new_value"]) == (row["verdict"], "failed")
    assert entry["device_uid"] == row["device_uid"]


@pytest.mark.parametrize("field", ["function", "verdict"])
def test_measurement_changes_of_substance_are_registered(service, stored, field):
    _, row, _, _ = stored
    new = "riso_ramp" if field == "function" else "failed"
    service.edit_measurement(row["id"], {field: new})
    assert [c["field"] for c in service.measurement_changes(row["id"])] == [field]


@pytest.mark.parametrize("field", ["lower_limit", "upper_limit", "verdict"])
def test_value_changes_of_substance_are_registered(service, stored, field):
    _, row, values, _ = stored
    new = "failed" if field == "verdict" else ">9MΩ"
    service.edit_measurement(row["id"], value_changes={values[0]["id"]: {field: new}})
    assert [c["field"] for c in service.measurement_changes(row["id"])] == [f"riso.{field}"]


@pytest.mark.parametrize("field", ["comment", "location"])
def test_correcting_a_text_leaves_no_trace(service, stored, field):
    campaign, row, _, _ = stored
    assert service.edit_measurement(row["id"], {field: "korrigiert"}) == 1
    assert service.measurements(campaign)[0][field] == "korrigiert"
    assert service.measurement_changes(row["id"]) == []


def test_correcting_a_label_leaves_no_trace(service, stored):
    _, row, values, _ = stored
    service.edit_measurement(row["id"], value_changes={values[0]["id"]: {"label": "RISO L1"}})
    assert service.values(row["id"])[0]["label"] == "RISO L1"
    assert service.measurement_changes(row["id"]) == []


def test_saving_without_a_change_leaves_no_trace(service, stored):
    _, row, _, _ = stored
    assert service.edit_measurement(row["id"], {"comment": row["comment"]}) == 0
    assert service.measurement_changes(row["id"]) == []


def test_the_log_cannot_be_rewritten(service, stored):
    _, row, _, _ = stored
    service.edit_measurement(row["id"], {"verdict": "failed"})
    with pytest.raises(sqlite3.IntegrityError):
        service.db.execute("UPDATE measurement_log SET new_value='x'")
    with pytest.raises(sqlite3.IntegrityError):
        service.db.execute("DELETE FROM measurement_log")


# Deleting --------------------------------------------------------------------


def test_deleted_measurement_is_gone_from_the_campaign(service, stored):
    campaign, row, _, _ = stored
    service.delete_measurement(row["id"])
    assert service.measurements(campaign) == []
    assert service.values(row["id"]) == []


def test_deleting_leaves_only_the_id_behind(service, stored):
    _, row, _, _ = stored
    service.delete_measurement(row["id"])
    entry = service.measurement_changes(row["id"])[0]
    assert (entry["device_uid"], entry["old_value"]) == (row["device_uid"], "")


def test_deleted_measurement_does_not_come_back_from_the_instrument(service, stored):
    campaign, row, _, meter = stored
    service.delete_measurement(row["id"])
    assert service.collect(campaign, meter)["added"] == 0


# In the report ---------------------------------------------------------------


def report_measurements(service, campaign):
    return [m for step in report_context(service, campaign)["steps"] for m in step.measurements]


def test_manual_measurement_is_marked_in_the_report(service, asset_id):
    campaign = service.create(asset_id, "T", "P")
    service.add_measurement(campaign, "other", [ResultValue("x", "X", Quantity.parse("1V"))])
    measurement = report_measurements(service, campaign)[0]
    assert measurement.manual
    assert _marks(measurement) == " (manuell)"


def test_overwritten_measurement_is_marked_in_the_report(service, asset_id):
    campaign = service.create(asset_id, "T", "P")
    row = service.add_measurement(campaign, "other", [])
    service.edit_measurement(row, {"verdict": "failed"})
    assert _marks(report_measurements(service, campaign)[0]) == " (manuell, geändert)"


def test_corrected_text_is_not_marked_in_the_report(service, stored):
    campaign, row, _, _ = stored
    service.edit_measurement(row["id"], {"comment": "Rechtschreibung", "location": "Schrank"})
    assert _marks(report_measurements(service, campaign)[0]) == ""


def test_deleted_measurement_is_not_mentioned_in_the_report(service, asset_id):
    campaign = service.create(asset_id, "T", "P")
    service.add_measurement(campaign, "other", [])
    twice = service.add_measurement(campaign, "other", [])
    service.delete_measurement(twice)
    measurements = report_measurements(service, campaign)
    assert len(measurements) == 1
    assert _marks(measurements[0]) == " (manuell)"


def test_untouched_measurement_has_no_mark(service, stored):
    campaign, _, _, _ = stored
    assert _marks(report_measurements(service, campaign)[0]) == ""


def test_answers_saved_together_show_their_time_once():
    from datetime import datetime, timedelta
    from types import SimpleNamespace

    from easymeasurement.reporting.measurement_words import clock_times

    at = datetime(2026, 5, 4, 10, 38, 12)
    rows = [SimpleNamespace(local_time=time, manual=manual, edited=False)
            for time, manual in ((at, False), (at, False), (at, True),
                                 (at + timedelta(minutes=1), False))]
    assert clock_times(rows) == ["10:38:12", "", "(manuell)", "10:39:12"]
