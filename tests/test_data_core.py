# EasyMeasurement - tests/test_data_core.py
# Customers, assets, measurements and values: no instrument involved.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date, datetime

import pytest
from PIL import Image

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.reporting.archive import ReportArchive
from easymeasurement.reporting.context import build_context
from easymeasurement.reporting.template import default_template_text
from easymeasurement.store import CampaignClosed
from easymeasurement.store.search import MeasurementFilter, search_measurements, search_reports

T0 = datetime(2026, 3, 1, 10, 0, 0)


def value(key, label, text, verdict=Verdict.NOT_EVALUATED):
    return ResultValue(key, label, Quantity.parse(text), verdict)


def photo(path, stamp=None):
    exif = Image.Exif()
    if stamp:
        exif[0x8769] = {36867: stamp}
    Image.new("RGB", (8, 8), (len(path.name) * 9 % 255, 0, 0)).save(path, exif=exif)
    return path


@pytest.fixture
def world(db, service):
    a = db.add_customer("Müller Maschinenbau", city="Köln")
    b = db.add_customer("Nordwerk AG")
    hall = db.add_asset(a, "installation", "Halle 3")
    press = db.add_asset(a, "machine", "Presse 7", parent_id=hall, identifier="M-007")
    pump = db.add_asset(b, "device", "Pumpe", identifier="P-1")
    first = service.create(press, "Wiederholungsprüfung", "A. Prüfer")
    second = service.create(pump, "Erstprüfung", "B. Prüfer")
    service.add_measurement(
        first, "riso", [value("riso", "RISO", "2.05MΩ", Verdict.PASSED)], T0,
        Verdict.PASSED, comment="Stromkreis F1",
    )
    service.add_measurement(
        first, "riso", [value("riso", "RISO", "900kΩ", Verdict.FAILED)],
        datetime(2026, 3, 2, 9, 0), Verdict.FAILED,
    )
    service.add_measurement(
        second, "rlo", [value("rlo", "RLO", "0.22Ω", Verdict.PASSED)],
        datetime(2026, 4, 1, 9, 0), Verdict.PASSED,
    )
    return {"a": a, "b": b, "hall": hall, "press": press, "pump": pump,
            "first": first, "second": second}


def find(db, **options):
    return search_measurements(db, MeasurementFilter(**options))


def test_measurement_needs_no_instrument_and_no_plan(world, service):
    assert len(service.measurements(world["first"])) == 2
    assert service.blockers(world["first"]) == []


def test_measurement_may_have_no_values(service, world):
    measurement = service.add_measurement(world["first"], "other", [], T0)
    assert service.values(measurement) == []


def test_measurement_may_have_many_values(service, world):
    readings = [value("u", f"U{n}", f"{230 + n}V") for n in range(4)]
    measurement = service.add_measurement(world["first"], "u", readings, T0)
    assert len(service.values(measurement)) == 4


def test_filter_by_customer(db, world):
    assert len(find(db, customer_id=world["b"])) == 1


def test_filter_by_parent_asset_includes_children(db, world):
    assert len(find(db, asset_id=world["hall"])) == 2


def test_filter_by_verdict(db, world):
    assert len(find(db, verdict="failed")) == 1


def test_filter_by_function(db, world):
    assert len(find(db, function="rlo")) == 1


def test_filter_by_date_range_includes_the_last_day(db, world):
    assert len(find(db, date_from=date(2026, 3, 2), date_to=date(2026, 3, 2))) == 1


def test_filter_by_value_compares_real_magnitudes(db, world):
    below_one_megohm = find(db, value_key="riso", value_max=1e6)
    assert [row["verdict"] for row in below_one_megohm] == ["failed"]


def test_range_without_a_chosen_value_stays_within_its_unit(db, service, world):
    service.add_measurement(world["second"], "u", [value("u", "U", "230V")], T0)
    found = find(db, value_max=1e6, value_unit="Ω")
    assert all("U 230V" not in row["value_text"] for row in found)
    assert len(found) == 2  # 900 kΩ and 0.22 Ω, not 2.05 MΩ


def test_text_search_finds_customer_with_umlaut_in_any_case(db, world):
    assert len(find(db, text="MÜLLER")) == 2


def test_text_search_finds_a_value(db, world):
    assert len(find(db, text="900kΩ")) == 1


def test_text_search_needs_every_word(db, world):
    assert len(find(db, text="presse F1")) == 1
    assert find(db, text="presse pumpe") == []


def test_text_search_treats_percent_literally(db, world):
    assert find(db, text="%") == []


def test_filters_combine(db, world):
    assert len(find(db, customer_id=world["a"], verdict="passed", text="F1")) == 1


def test_results_carry_the_whole_path(db, world):
    row = find(db, text="F1")[0]
    assert (row["customer_name"], row["asset_name"]) == ("Müller Maschinenbau", "Presse 7")
    assert row["value_text"] == "RISO 2.05MΩ"


def test_photo_belongs_to_its_measurement_and_is_no_reading(service, world, tmp_path):
    measurement = service.measurements(world["first"])[0]["id"]
    service.add_photo(measurement, photo(tmp_path / "a.jpg"))
    assert [row["original_name"] for row in service.photos_of(measurement)] == ["a.jpg"]
    assert [v["kind"] for v in service.values(measurement)] == ["number"]


def test_photo_is_found_by_filter_and_file_name(db, service, world, tmp_path):
    measurement = service.measurements(world["first"])[0]["id"]
    service.add_photo(measurement, photo(tmp_path / "typenschild.jpg"))
    assert [r["id"] for r in find(db, has_photo=True)] == [measurement]
    assert [r["id"] for r in find(db, text="typenschild")] == [measurement]
    assert len(find(db, has_photo=False)) == 2


def test_photo_matches_by_time_into_a_measurement(service, world, tmp_path):
    result = service.import_photos(
        world["first"], [photo(tmp_path / "a.jpg", "2026:03:01 10:00:20")]
    )
    assert result["matched"] == 1
    row = service.db.one("SELECT * FROM measurements WHERE comment='Stromkreis F1'")
    assert len(service.photo_paths(row["id"])) == 1


def test_values_are_frozen_with_the_campaign(db, service, world, tmp_path):
    measurement = service.measurements(world["first"])[0]["id"]
    service.add_photo(measurement, photo(tmp_path / "a.jpg"))
    row = service.values(measurement)[0]
    service.close(world["first"])
    with pytest.raises(CampaignClosed):
        db.execute("UPDATE measured_values SET raw='1MΩ' WHERE id=?", row["id"])
    with pytest.raises(CampaignClosed):
        db.execute("DELETE FROM measured_values WHERE id=?", row["id"])
    with pytest.raises(CampaignClosed):
        service.add_measurement(world["first"], "u", [], T0)
    with pytest.raises(CampaignClosed):
        service.add_photo(measurement, photo(tmp_path / "b.jpg"))


def test_report_without_plan_groups_by_function(service, world):
    steps = build_context(service, world["first"])["steps"]
    assert [(s.function, len(s.measurements)) for s in steps] == [("riso", 2)]


def test_report_ignores_photos_for_the_verdict(service, world, tmp_path):
    service.import_photos(world["second"], [photo(tmp_path / "a.jpg", "2026:09:09 09:09:09")])
    assert build_context(service, world["second"])["verdict"] == "Bestanden"


def test_report_shows_photo_values_and_is_searchable(db, service, world, tmp_path):
    measurement = service.measurements(world["second"])[0]["id"]
    service.add_photo(measurement, photo(tmp_path / "a.jpg"))
    service.close(world["second"])
    archive = ReportArchive(service)
    archive.generate(world["second"], "Standard", default_template_text())
    assert len(search_reports(db, text="nordwerk")) == 1
    assert search_reports(db, text="müller") == []
    assert len(search_reports(db, asset_id=world["pump"])) == 1
    assert search_reports(db, signed=True) == []
