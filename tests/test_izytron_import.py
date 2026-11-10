# EasyMeasurement - tests/test_izytron_import.py
# Importing a day of testing from an IZYTRON database. All data here is invented.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import sqlite3
from datetime import date, datetime

import pytest

from easymeasurement.importing.izytron import ImportFailed, import_day
from easymeasurement.model import (
    CONDUCTOR,
    MeterMeasurement,
    Parameter,
    Quantity,
    ResultValue,
    Verdict,
    conductor_of,
)
from easymeasurement.reporting.context import ReportMeasurement, build_context
from easymeasurement.reporting.template import _many
from easymeasurement.store import CampaignClosed

from .izytron_helpers import build

OFFSET = -648


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "izytron.sqlite"
    build(path)
    return path


@pytest.fixture
def imported(service, source):
    return import_day(service, source, OFFSET)


def reading(service, campaign, function, index=0):
    rows = [m for m in service.measurements(campaign) if m["function"] == function]
    return rows[index], service.load_measurement(rows[index])


def test_day_becomes_one_campaign_open_for_review(service, imported):
    campaign = service.campaign(imported.campaign_id)
    assert campaign["status"] == "open"
    assert campaign["tester"] == "A. Prüfer"
    assert "22.10.2026" in campaign["title"]


def test_campaign_keeps_the_real_dates(service, imported):
    service.close(imported.campaign_id)
    campaign = service.campaign(imported.campaign_id)
    assert campaign["started_at"] == "2026-10-22T10:30:00"
    assert campaign["closed_at"] == "2026-10-22T11:13:48"


def test_counts(imported):
    assert (imported.measurements, imported.checks, imported.assets) == (4, 2, 3)


def test_deleted_rows_stay_out(service, imported):
    assert not [a for a in service.db.assets() if a["name"] == "Gelöscht"]
    assert len(service.measurements(imported.campaign_id)) == 6


def test_tree_is_rebuilt_with_kinds_and_guids(service, imported):
    assets = {a["name"]: a for a in service.db.assets()}
    assert assets["Presse"]["kind"] == "machine"
    assert assets["Presse"]["parent_id"] is None
    assert assets["Presse"]["guid"] == "mach"
    assert assets["Presse"]["serial_no"] == "S-1"
    assert assets["Schrank"]["parent_id"] == assets["Presse"]["id"]
    assert assets["Punkt"]["kind"] == "measuring_point"
    assert assets["Punkt"]["parent_id"] == assets["Schrank"]["id"]


def test_campaign_belongs_to_the_machine(service, imported):
    asset = service.db.asset(service.campaign(imported.campaign_id)["asset_id"])
    assert asset["name"] == "Presse"


def test_each_measurement_knows_its_part(service, imported):
    row, _ = reading(service, imported.campaign_id, "rlo")
    asset = service.db.asset(row["asset_id"])
    assert asset["name"] == "Punkt"
    assert row["location"] == "Presse / Schrank / Punkt"


def test_values_are_written_as_the_instrument_showed_them(service, imported):
    _, riso = reading(service, imported.campaign_id, "riso")
    value_ = riso.result("riso")
    assert value_.quantity.raw == ">1.20GΩ"
    assert value_.quantity.base_value == pytest.approx(1.2e9)
    assert value_.quantity.base_unit == "Ω"
    assert value_.lower_limit == ">1.00MΩ"
    assert riso.result("u_iso").quantity.raw == "519V"


def test_side_value_without_a_limit_is_not_evaluated(service, imported):
    _, riso = reading(service, imported.campaign_id, "riso")
    assert riso.result("u_iso").verdict is Verdict.NOT_EVALUATED


def test_three_phase_reading_with_rotation(service, imported):
    _, u3 = reading(service, imported.campaign_id, "u3")
    assert u3.result("rotation").quantity.raw == "right"
    assert u3.result("u_l3l1").quantity.raw == "398V"


def test_failed_measurement_stays_failed(service, imported):
    _, failed = reading(service, imported.campaign_id, "rlo", 1)
    assert failed.verdict is Verdict.FAILED
    assert failed.result("rlo").quantity.raw == ">199Ω"


def test_device_times_are_corrected_and_kept(service, imported):
    row, _ = reading(service, imported.campaign_id, "riso")
    assert row["device_time"] == "2026-10-22T11:00:00"
    assert row["local_time"] == "2026-10-22T11:10:48"
    assert row["clock_offset_s"] == OFFSET


def test_sight_check_was_entered_in_local_time(service, imported):
    row, _ = reading(service, imported.campaign_id, "visual_inspection")
    assert row["local_time"] == "2026-10-22T10:30:00"
    assert row["device_time"] is None


def test_sight_check_keeps_question_answer_and_remark(service, imported):
    _, check = reading(service, imported.campaign_id, "visual_inspection")
    assert check.result("question").quantity.raw == "Sind Warnhinweise angebracht?"
    assert check.result("answer").quantity.raw == "yes"
    assert check.result("note").quantity.raw == "Am Schrank innen"


def test_instrument_and_overdue_calibration_are_known(service, imported):
    identity = service.identity(imported.campaign_id)
    assert identity.serial_no == "TEST0001"
    assert identity.calibrated_on == date(2023, 2, 13)
    assert identity.recalibration_due == date(2024, 8, 13)
    assert build_context(service, imported.campaign_id)["device"]["overdue"] is True


def test_offset_shows_up_in_the_report_data(service, imported):
    summary = build_context(service, imported.campaign_id)["campaign"]["clock_summary"]
    assert "-648 s" in summary


def test_parameters_are_readable(service, imported):
    _, riso = reading(service, imported.campaign_id, "riso")
    assert [(p.key, p.value) for p in riso.parameters] == [("RISO - Leiter", "L1-PE")]


def test_original_record_is_kept(service, imported):
    row, _ = reading(service, imported.campaign_id, "riso")
    assert "PROFITEST_TS1165" in row["raw_data"]


def test_importing_twice_is_refused(service, source, imported):
    with pytest.raises(ImportFailed, match="schon importiert"):
        import_day(service, source, OFFSET)
    assert len(service.campaigns()) == 1


def test_existing_customer_is_reused(service, source):
    existing = service.db.add_customer("MUSTER AG")
    import_day(service, source, OFFSET)
    assert [c["id"] for c in service.db.customers()] == [existing]


def test_imported_campaign_can_be_reviewed_before_closing(service, imported):
    row, _ = reading(service, imported.campaign_id, "riso")
    service.edit_measurement(row["id"], {"location": "Presse / Schrank / F1"})
    assert reading(service, imported.campaign_id, "riso")[0]["location"].endswith("F1")


def test_imported_campaign_is_frozen_once_closed(service, imported):
    row, _ = reading(service, imported.campaign_id, "riso")
    service.close(imported.campaign_id)
    with pytest.raises(CampaignClosed):
        service.db.execute("UPDATE measurements SET comment='x' WHERE id=?", row["id"])


def test_source_database_is_not_changed(service, source):
    before = source.read_bytes()
    import_day(service, source, OFFSET)
    assert source.read_bytes() == before


def test_empty_database_is_refused(service, tmp_path):
    path = tmp_path / "leer.sqlite"
    build(path)
    connection = sqlite3.connect(path)
    connection.execute("DELETE FROM Testing")
    connection.commit()
    connection.close()
    with pytest.raises(ImportFailed, match="keine Prüfungen"):
        import_day(service, path, OFFSET)


def test_report_table_names_conductor_and_place(service, source):
    result = import_day(service, source, OFFSET)
    steps = build_context(service, result.campaign_id)["steps"]
    step = next(s for s in steps if s.function == "rlo")
    assert all(conductor_of(m.data.parameters) == "L1-PE" for m in step.measurements)
    nodes = _many(step.measurements, {"summary": True})
    assert nodes[0].headers[:4] == ["Nr.", "Zeitpunkt", "Messort", "Leiter"]
    assert nodes[0].rows[0][3] == "L1-PE"
    assert len(nodes[0].summary[0]) == len(nodes[0].headers)


def conductor_group(*conductors):
    return [
        ReportMeasurement(
            MeterMeasurement(
                uid=str(number), function="u", taken_at=datetime(2026, 1, 1, 9, number),
                verdict=Verdict.PASSED, parameters=(Parameter(CONDUCTOR, conductor),),
                results=(ResultValue("u", "U", Quantity.parse("225V")),),
            ),
            datetime(2026, 1, 1, 9, number),
        )
        for number, conductor in enumerate(conductors)
    ]


def test_different_conductors_get_no_min_and_max():
    table = _many(conductor_group("L1-PE", "L1-L2"), {"summary": True})[0]
    assert table.summary == []


def test_same_conductor_keeps_min_and_max():
    table = _many(conductor_group("L1-PE", "L1-PE"), {"summary": True})[0]
    assert [row[0] for row in table.summary] == ["Min", "Max"]


def test_a_visual_inspection_is_one_run_of_named_steps(service, imported):
    rows = [m for m in service.measurements(imported.campaign_id)
            if m["function"] == "visual_inspection"]
    assert {row["run_id"] for row in rows} == {rows[0]["run_id"]}
    assert [row["step_name"] for row in rows] == ["Warnhinweise", "Schutzleiter"]
    run = service.run(rows[0]["run_id"])
    assert (run["name"], run["kind"]) == ("Sichtprüfung der Betriebsmittel", "Sichtprüfung")
    device = [m for m in service.measurements(imported.campaign_id) if m["function"] == "rlo"]
    assert all(row["run_id"] is None for row in device)  # a reading from the device is no run
