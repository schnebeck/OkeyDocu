# OkeyDocu - tests/test_campaign_record.py
# Photos of a campaign, closing it, and the frozen record.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from PIL import Image

from okeydocu.campaign.photos import read_photo_time
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.store import CampaignClosed

from .campaign_helpers import T0, start, step_of


def write_jpeg(path, stamp=None, offset=None):
    image = Image.new("RGB", (8, 8))
    exif = Image.Exif()
    if stamp:
        exif[0x8769] = {36867: stamp, **({36881: offset} if offset else {})}
    image.save(path, exif=exif)
    return path


def test_exif_time_wins_over_file_name(tmp_path):
    path = write_jpeg(tmp_path / "IMG_20200101_000000.jpg", "2026:03:01 10:00:30")
    assert read_photo_time(path) == (datetime(2026, 3, 1, 10, 0, 30), "exif")


def test_exif_offset_is_converted_to_local_time(tmp_path):
    path = write_jpeg(tmp_path / "a.jpg", "2026:03:01 10:00:30", "+00:00")
    moment, source = read_photo_time(path)
    expected = datetime.fromisoformat("2026-03-01T10:00:30+00:00").astimezone().replace(tzinfo=None)
    assert (moment, source) == (expected, "exif")


def test_file_name_is_the_fallback(tmp_path):
    path = tmp_path / "IMG_20260301_100030.png"
    Image.new("RGB", (4, 4)).save(path)
    assert read_photo_time(path) == (datetime(2026, 3, 1, 10, 0, 30), "filename")


def test_pixel_file_names_are_utc(tmp_path):
    path = tmp_path / "PXL_20260301_100030123.png"
    Image.new("RGB", (4, 4)).save(path)
    expected = datetime.fromisoformat("2026-03-01T10:00:30+00:00").astimezone().replace(tzinfo=None)
    assert read_photo_time(path) == (expected, "filename")


def test_photo_without_any_time_stays_unknown(tmp_path):
    path = tmp_path / "foto.png"
    Image.new("RGB", (4, 4)).save(path)
    assert read_photo_time(path) == (None, "unknown")


def test_photo_import_uses_corrected_times_and_skips_duplicates(service, asset_id, plan, tmp_path):
    skew = 3000
    meter = SimulatedMeter(clock_skew_s=skew, seed=1)
    campaign = start(service, asset_id, plan, meter)
    step = step_of(service, campaign, "rlo")
    now = datetime.now().replace(microsecond=0)
    service.confirm_setup(step["id"], now=now)
    meter.simulate_measurement("rlo", at=now + timedelta(seconds=10))
    service.collect(campaign, meter)
    stamp = (now + timedelta(seconds=25)).strftime("%Y:%m:%d %H:%M:%S")
    photo = write_jpeg(tmp_path / "a.jpg", stamp)
    assert service.import_photos(campaign, [photo])["matched"] == 1
    assert service.import_photos(campaign, [photo])["duplicates"] == 1
    assert service.photos(campaign)[0]["step_id"] == step["id"]


def test_phone_clock_offset_is_applied(service, asset_id, plan, tmp_path):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    step = step_of(service, campaign, "rlo")
    now = datetime.now().replace(microsecond=0)
    service.confirm_setup(step["id"], now=now)
    meter.simulate_measurement("rlo", at=now + timedelta(seconds=10))
    service.collect(campaign, meter)
    stamp = (now + timedelta(minutes=30)).strftime("%Y:%m:%d %H:%M:%S")
    photo = write_jpeg(tmp_path / "a.jpg", stamp)
    service.set_photo_shift(campaign, -1800)
    assert service.import_photos(campaign, [photo])["matched"] == 1
    assert service.photos(campaign)[0]["step_id"] == step["id"]


def finish_all(service, campaign):
    for step in service.steps(campaign):
        service.skip_step(step["id"], "Test")


def test_campaign_cannot_close_with_open_steps(service, asset_id, plan):
    campaign = start(service, asset_id, plan, SimulatedMeter(seed=1))
    with pytest.raises(ValueError, match="Schritt offen"):
        service.close(campaign)


def test_campaign_cannot_close_with_unassigned_measurements(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    meter.simulate_measurement("rlo", at=T0)
    service.collect(campaign, meter)
    finish_all(service, campaign)
    with pytest.raises(ValueError, match="keinem Schritt"):
        service.close(campaign)


def test_closed_campaign_is_frozen(service, db, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    step = step_of(service, campaign, "rlo")
    service.confirm_setup(step["id"], now=T0)
    meter.simulate_measurement("rlo", at=T0 + timedelta(seconds=5))
    service.collect(campaign, meter)
    finish_all(service, campaign)
    service.close(campaign)
    row = service.measurements(campaign)[0]
    with pytest.raises(CampaignClosed):
        db.execute("UPDATE measurements SET verdict='passed' WHERE id=?", row["id"])
    with pytest.raises(CampaignClosed):
        db.execute("DELETE FROM measurements WHERE id=?", row["id"])
    with pytest.raises(CampaignClosed):
        db.execute("UPDATE campaigns SET status='open' WHERE id=?", campaign)
    with pytest.raises(CampaignClosed):
        service.skip_step(step["id"], "nachträglich")


def test_stored_measurement_round_trips(service, asset_id, plan):
    meter = SimulatedMeter(seed=1)
    campaign = start(service, asset_id, plan, meter)
    original = meter.simulate_measurement("riso", at=T0)
    service.collect(campaign, meter)
    loaded = service.load_measurement(service.measurements(campaign)[0])
    assert loaded == replace(original, operator=service.campaign(campaign)["tester"])
