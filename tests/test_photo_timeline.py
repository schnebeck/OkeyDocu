# EasyMeasurement - tests/test_photo_timeline.py
# Photos on the timeline: shift, gaps, the stack, and pinning by hand.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

import pytest
from PIL import Image

from easymeasurement.campaign.photos import nearest_measurement, timeline_time
from easymeasurement.store import CampaignClosed

T0 = datetime(2026, 3, 1, 10, 0, 0)
EXIF_DATETIME_ORIGINAL = 36867
EXIF_IFD = 0x8769


def write_photo(path, moment=None, colour=None):
    image = Image.new("RGB", (4, 4), colour or (hash(path.name) % 255, 10, 10))
    exif = image.getexif()
    if moment:
        exif.get_ifd(EXIF_IFD)[EXIF_DATETIME_ORIGINAL] = moment.strftime("%Y:%m:%d %H:%M:%S")
    image.save(path, exif=exif)
    return path


@pytest.fixture
def campaign(service, asset_id):
    return service.create(asset_id, "T", "P")


@pytest.fixture
def measured(service, campaign):
    """Measurements at minute 0, 10 and 20."""
    return [
        service.add_measurement(campaign, "rlo", [], T0 + timedelta(minutes=minute))
        for minute in (0, 10, 20)
    ]


def owners(service, campaign):
    return [row["measurement_id"] for row in service.photos(campaign)]


def import_at(service, campaign, tmp_path, *minutes):
    files = [
        write_photo(tmp_path / f"{minute}.jpg", T0 + timedelta(minutes=minute))
        for minute in minutes
    ]
    return service.import_photos(campaign, files)


# The arithmetic --------------------------------------------------------------


def test_shift_moves_a_photo():
    assert timeline_time(T0, 60, []) == T0 + timedelta(seconds=60)


def test_gap_moves_what_comes_after_it():
    gap = [(T0, 30)]
    assert timeline_time(T0 + timedelta(seconds=1), 0, gap) == T0 + timedelta(seconds=31)


def test_gap_leaves_what_comes_before_it():
    gap = [(T0, 30)]
    assert timeline_time(T0 - timedelta(seconds=1), 0, gap) == T0 - timedelta(seconds=1)


def test_gaps_add_up():
    assert timeline_time(T0, 0, [(T0, 30), (T0, 10)]) == T0 + timedelta(seconds=40)


def test_nearest_measurement_wins():
    measured = [(1, T0), (2, T0 + timedelta(seconds=60))]
    assert nearest_measurement(T0 + timedelta(seconds=40), measured) == 2


def test_equal_distance_goes_to_the_earlier_one():
    measured = [(2, T0 + timedelta(seconds=20)), (1, T0)]
    assert nearest_measurement(T0 + timedelta(seconds=10), measured) == 1


def test_no_measurement_no_owner():
    assert nearest_measurement(T0, []) is None


# On the timeline -------------------------------------------------------------


def test_photos_go_to_the_nearest_measurement(service, campaign, measured, tmp_path):
    result = import_at(service, campaign, tmp_path, 1, 11)
    assert result == {"added": 2, "matched": 2, "open": 0, "duplicates": 0}
    assert owners(service, campaign) == measured[:2]


def test_a_photo_far_away_still_goes_to_the_nearest(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 500)
    assert owners(service, campaign) == [measured[2]]


def test_photo_without_a_time_lands_on_the_stack(service, campaign, measured, tmp_path):
    result = service.import_photos(campaign, [write_photo(tmp_path / "x.png")])
    assert result["open"] == 1
    assert [row["original_name"] for row in service.stacked_photos(campaign)] == ["x.png"]


def test_shift_moves_all_photos_to_other_measurements(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    service.set_photo_shift(campaign, 600)
    assert owners(service, campaign) == measured[1:]


def test_start_puts_the_first_photo_at_that_moment(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    service.set_photo_start(campaign, T0 + timedelta(minutes=10))
    assert owners(service, campaign) == measured[1:]
    assert service.campaign(campaign)["photo_shift_s"] == 540


def test_start_counts_a_gap_before_the_first_photo(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    service.add_photo_gap(campaign, T0, 60)
    service.set_photo_start(campaign, T0 + timedelta(minutes=10))
    assert service.campaign(campaign)["photo_shift_s"] == 480


def test_a_gap_can_change_its_length(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    gap = service.add_photo_gap(campaign, T0 + timedelta(minutes=5), 60)
    service.resize_photo_gap(gap, 600)
    assert service.photo_gaps(campaign)[0]["id"] == gap
    assert owners(service, campaign) == [measured[0], measured[2]]


def test_the_time_a_photo_was_taken_stays(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    before = service.photos(campaign)[0]["taken_at"]
    service.set_photo_shift(campaign, 600)
    assert service.photos(campaign)[0]["taken_at"] == before


def test_gap_stretches_the_end_of_the_stack(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    service.add_photo_gap(campaign, T0 + timedelta(minutes=5), 600)
    assert owners(service, campaign) == [measured[0], measured[2]]


def test_removing_a_gap_lets_the_photos_move_back(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    gap = service.add_photo_gap(campaign, T0 + timedelta(minutes=5), 600)
    service.remove_photo_gap(gap)
    assert owners(service, campaign) == measured[:2]


# Off the timeline ------------------------------------------------------------


def test_removing_a_photo_keeps_the_file_and_the_others(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1, 11)
    first, second = service.photos(campaign)
    service.stack_photo(first["id"])
    path = service.photo_path(campaign, first["file_name"])
    assert path.exists()
    assert [row["id"] for row in service.stacked_photos(campaign)] == [first["id"]]
    assert service.photos_of(measured[1])[0]["id"] == second["id"]


def test_timeline_leaves_the_stack_alone(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    service.stack_photo(service.photos(campaign)[0]["id"])
    service.set_photo_shift(campaign, 600)
    assert owners(service, campaign) == [None]


def test_pinned_photo_ignores_the_timeline(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    service.pin_photo(service.photos(campaign)[0]["id"], measured[2])
    service.set_photo_shift(campaign, 60)
    assert owners(service, campaign) == [measured[2]]


def test_a_photo_can_return_to_the_timeline(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    photo = service.photos(campaign)[0]["id"]
    service.stack_photo(photo)
    service.return_to_timeline(photo)
    assert owners(service, campaign) == [measured[0]]


def test_a_photo_without_a_time_cannot_return(service, campaign, measured, tmp_path):
    service.import_photos(campaign, [write_photo(tmp_path / "x.png")])
    photo = service.photos(campaign)[0]["id"]
    service.return_to_timeline(photo)
    assert len(service.stacked_photos(campaign)) == 1


def test_deleting_a_photo_removes_its_file(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    row = service.photos(campaign)[0]
    path = service.photo_path(campaign, row["file_name"])
    service.delete_photo(row["id"])
    assert not path.exists()
    assert service.photos(campaign) == []


def test_pinning_a_known_photo_adds_no_second_one(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    service.add_photo(measured[2], tmp_path / "1.jpg")
    assert owners(service, campaign) == [measured[2]]


# With the measurements -------------------------------------------------------


def test_deleted_measurement_hands_its_photos_on(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    service.delete_measurement(measured[0])
    assert owners(service, campaign) == [measured[1]]


def test_deleted_measurement_sends_a_pinned_photo_to_the_stack(
    service, campaign, measured, tmp_path
):
    import_at(service, campaign, tmp_path, 1)
    service.pin_photo(service.photos(campaign)[0]["id"], measured[2])
    service.delete_measurement(measured[2])
    assert len(service.stacked_photos(campaign)) == 1


def test_closed_campaign_freezes_the_timeline(service, campaign, measured, tmp_path):
    import_at(service, campaign, tmp_path, 1)
    photo = service.photos(campaign)[0]["id"]
    service.close(campaign)
    with pytest.raises(CampaignClosed):
        service.stack_photo(photo)
    with pytest.raises(CampaignClosed):
        service.add_photo_gap(campaign, T0, 10)
    with pytest.raises(CampaignClosed):
        service.set_photo_shift(campaign, 60)
