# EasyMeasurement - tests/test_seal.py
# After closing, the record can be proven unchanged, and manipulation is noticed.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PIL import Image

from easymeasurement.campaign.seal import SealState, authenticate, digest

from . import seal_helpers
from .seal_helpers import finished, forge

# pytest looks fixtures up by name in the test module.
asset, path, sealing = seal_helpers.asset, seal_helpers.path, seal_helpers.sealing


# Sealing ---------------------------------------------------------------------


def test_closing_seals_the_campaign(sealing, asset):
    campaign = sealing.campaign(finished(sealing, asset))
    assert len(campaign["seal"]) == 64
    assert len(campaign["seal_mac"]) == 64
    assert campaign["sealed_at"]


def test_a_sealed_campaign_passes_the_check(sealing, asset):
    assert sealing.check_seal(finished(sealing, asset)).state is SealState.INTACT


def test_open_campaign_has_nothing_to_check(sealing, asset):
    campaign = sealing.create(asset, "T", "P")
    assert sealing.check_seal(campaign).state is SealState.OPEN


def test_seal_does_not_depend_on_row_numbers(sealing, asset):
    campaign = finished(sealing, asset)
    row = sealing.campaign(campaign)
    forge(sealing.db.path, "UPDATE measured_values SET id = id + 1000")
    assert digest(sealing.db, campaign, row["closed_at"]) == row["seal"]


def test_the_chain_links_each_seal_to_the_one_before(sealing, asset):
    first = sealing.campaign(finished(sealing, asset, "Erste"))
    second = sealing.campaign(finished(sealing, asset, "Zweite"))
    assert first["seal_previous"] == ""
    assert second["seal_previous"] == first["seal"]


# Manipulation ----------------------------------------------------------------


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE measured_values SET raw='0.10Ω'",
        "UPDATE measured_values SET base_value=0.1",
        "UPDATE measurements SET verdict='failed'",
        "UPDATE measurements SET local_time='2020-01-01T00:00:00'",
        "UPDATE measurements SET comment='anders'",
        "UPDATE campaigns SET tester='Jemand anders'",
        "UPDATE campaigns SET title='Andere Prüfung'",
        "DELETE FROM measured_values",
        "DELETE FROM measurements",
        "INSERT INTO measurements (campaign_id, device_uid, source, function, local_time, verdict)"
        " VALUES (1, 'neu', 'manual', 'rlo', '2026-01-01T00:00:00', 'passed')",
    ],
)
def test_changes_behind_the_apps_back_are_noticed(sealing, asset, statement):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, statement)
    check = sealing.check_seal(campaign)
    assert check.rejected
    assert check.reasons


def test_quick_check_notices_it_too(sealing, asset):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, "UPDATE measured_values SET raw='0.10Ω'")
    assert sealing.check_seal(campaign, thorough=False).rejected


def test_recomputing_the_digest_does_not_help_without_the_key(sealing, asset):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, "UPDATE measured_values SET raw='0.10Ω'")
    row = sealing.campaign(campaign)
    forged = digest(sealing.db, campaign, row["closed_at"])
    forge(sealing.db.path, f"UPDATE campaigns SET seal='{forged}'")
    check = sealing.check_seal(campaign)
    assert check.rejected
    assert "nicht echt" in check.reasons[0]


def test_a_forged_authentication_with_a_guessed_key_fails(sealing, asset):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, "UPDATE measured_values SET raw='0.10Ω'")
    row = sealing.campaign(campaign)
    forged = digest(sealing.db, campaign, row["closed_at"])
    mac = authenticate(b"geraten", forged, row["seal_previous"])
    forge(sealing.db.path, f"UPDATE campaigns SET seal='{forged}', seal_mac='{mac}'")
    assert sealing.check_seal(campaign).rejected


def test_removing_the_authentication_is_noticed(sealing, asset):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, "UPDATE campaigns SET seal_mac=''")
    assert sealing.check_seal(campaign).rejected


def test_removing_a_seal_from_the_chain_is_noticed(sealing, asset):
    first = finished(sealing, asset, "Erste")
    second = finished(sealing, asset, "Zweite")
    forge(sealing.db.path, f"DELETE FROM measured_values WHERE measurement_id IN"
          f" (SELECT id FROM measurements WHERE campaign_id={first})",
          f"DELETE FROM measurements WHERE campaign_id={first}",
          f"DELETE FROM campaigns WHERE id={first}")
    check = sealing.check_seal(second)
    assert check.rejected
    assert "fehlt" in check.reasons[0]


def photo_campaign(service, asset, tmp_path):
    campaign = service.create(asset, "T", "P")
    measurement = service.add_measurement(campaign, "other", [])
    source = tmp_path / "foto.png"
    Image.new("RGB", (4, 4), "red").save(source)
    service.add_photo(measurement, source)
    service.close(campaign)
    return campaign, service.photo_paths(measurement)[0]


def test_changed_photo_file_is_noticed(sealing, asset, tmp_path):
    campaign, photo = photo_campaign(sealing, asset, tmp_path)
    assert sealing.check_seal(campaign).state is SealState.INTACT
    Image.new("RGB", (4, 4), "blue").save(photo, format="PNG")
    assert "verändert" in sealing.check_seal(campaign).reasons[0]


def test_missing_photo_file_is_noticed(sealing, asset, tmp_path):
    campaign, photo = photo_campaign(sealing, asset, tmp_path)
    photo.unlink()
    assert "fehlt" in sealing.check_seal(campaign).reasons[0]
