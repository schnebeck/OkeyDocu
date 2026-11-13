# OkeyDocu - tests/test_photo_data_ui.py
# The snapshot of the timeline agrees with the backend arithmetic.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import random
from datetime import datetime, timedelta

from okeydocu.campaign.photos import nearest_measurement, timeline_time
from okeydocu.ui.photo_timeline_data import TimelineData, TrackGap, TrackMark, TrackPhoto
from okeydocu.ui.photo_timeline_model import to_moment, to_seconds

from .photo_ui_helpers import T0


def mark(mark_id, minute):
    return TrackMark(mark_id, to_seconds(T0 + timedelta(minutes=minute)), "passed", "RLO")


def photo(photo_id, minute, placement="timeline", owner=None):
    taken = None if minute is None else T0 + timedelta(minutes=minute)
    return TrackPhoto(photo_id, placement, owner, taken, f"{photo_id}.jpg", f"{photo_id}.jpg")


def gap(gap_id, minute, seconds):
    return TrackGap(gap_id, T0 + timedelta(minutes=minute), seconds)


def test_nearest_mark_agrees_with_the_backend():
    rng = random.Random(7)
    moments = sorted(T0 + timedelta(seconds=rng.randint(0, 3000)) for _ in range(60))
    moments += moments[:3]  # the same moment twice
    moments.sort()
    measured = list(enumerate(moments, 1))
    data = TimelineData(
        [TrackMark(i, to_seconds(at), "passed", "") for i, at in measured], [], []
    )
    for _ in range(500):
        moment = T0 + timedelta(seconds=rng.randint(-200, 3300))
        assert data.nearest_mark(to_seconds(moment)).id == nearest_measurement(moment, measured)


def test_equal_distance_goes_to_the_earlier_mark():
    data = TimelineData([mark(1, 0), mark(2, 2)], [], [])
    assert data.nearest_mark(to_seconds(T0 + timedelta(minutes=1))).id == 1


def test_places_follow_the_backend_with_shift_and_gaps():
    gaps = [gap(1, 5, 120), gap(2, 5, 30), gap(3, 8, 10)]
    photos = [photo(1, 4), photo(2, 5), photo(3, 9)]
    data = TimelineData([], photos, gaps, shift=45)
    pairs = [(g.at, g.seconds) for g in gaps]
    places = data.places()
    for item in photos:
        assert places[item.id] == to_seconds(timeline_time(item.taken, 45, pairs))


def test_a_pinned_photo_stands_at_its_measurement_whatever_the_shift():
    data = TimelineData([mark(7, 3)], [photo(1, 50, "pinned", 7)], [], shift=999)
    assert data.places()[1] == to_seconds(T0 + timedelta(minutes=3))


def test_a_pinned_photo_without_a_time_is_placed_too():
    data = TimelineData([mark(7, 3)], [photo(1, None, "pinned", 7)], [])
    assert data.places()[1] == to_seconds(T0 + timedelta(minutes=3))
    assert data.owners(data.places()) == {1: 7}


def test_owners_change_with_the_shift_and_pinned_ones_do_not():
    data = TimelineData(
        [mark(1, 0), mark(2, 10)], [photo(1, 1, owner=1), photo(2, 1, "pinned", 1)], []
    )
    data.shift = 600
    assert data.owners(data.places()) == {1: 2, 2: 1}
    assert data.changed_owners() == 1


def test_gaps_at_one_moment_stand_in_a_row():
    data = TimelineData([], [], [gap(1, 5, 60), gap(2, 5, 30)], shift=10)
    spans = data.gap_spans()
    start = to_seconds(T0 + timedelta(minutes=5)) + 10
    assert spans[1] == (start, start + 60)
    assert spans[2] == (start + 60, start + 90)


def test_a_later_gap_stands_behind_an_earlier_one():
    data = TimelineData([], [], [gap(1, 5, 60), gap(2, 8, 30)])
    assert data.gap_spans()[2][0] == to_seconds(T0 + timedelta(minutes=9))


def test_original_time_turns_the_timeline_around():
    gaps = [gap(1, 5, 120), gap(2, 9, 45)]
    data = TimelineData([], [], gaps, shift=33)
    pairs = [(g.at, g.seconds) for g in gaps]
    for minute in (1, 6, 8, 12):
        taken = T0 + timedelta(minutes=minute, seconds=7)
        place = to_seconds(timeline_time(taken, 33, pairs))
        assert data.original_time(place) == taken


def test_inside_a_gap_the_moment_is_where_the_gap_starts():
    data = TimelineData([], [], [gap(1, 5, 120)])
    assert data.original_time(to_seconds(T0 + timedelta(minutes=6))) == T0 + timedelta(minutes=5)


def test_start_counts_a_gap_in_front_of_the_first_photo():
    data = TimelineData([], [photo(1, 10), photo(2, 20)], [gap(1, 5, 60)])
    wanted = T0 + timedelta(minutes=30)
    data.shift = data.shift_for_start(wanted)
    assert data.first_place() == wanted


def test_first_photo_is_taken_from_the_timeline_only():
    data = TimelineData([mark(1, 0)], [photo(1, 1, "pinned", 1), photo(2, 5)], [])
    assert data.first_taken() == T0 + timedelta(minutes=5)


def test_nothing_placed_has_no_start():
    assert TimelineData([], [], []).shift_for_start(T0) is None
    assert TimelineData([], [], []).first_place() is None


def test_content_range_holds_marks_photos_and_gaps():
    data = TimelineData([mark(1, 0)], [photo(1, 5)], [gap(1, 20, 600)])
    assert data.content_range() == (
        to_seconds(T0), to_seconds(T0 + timedelta(minutes=30)),
    )
    assert TimelineData([], [], []).content_range() is None


def test_empty_tracks_say_what_to_do():
    marks_text, photos_text = TimelineData([], [], []).empty_texts()
    assert "Messungen" in marks_text
    assert "importieren" in photos_text
    assert TimelineData([mark(1, 0)], [photo(1, 1)], []).empty_texts() == ("", "")


def test_rows_become_a_snapshot_without_the_stack():
    rows = [
        {"id": 1, "placement": "timeline", "measurement_id": 3, "file_name": "a.jpg",
         "original_name": "a.jpg", "taken_at": "2026-03-01T10:00:00"},
        {"id": 2, "placement": "stack", "measurement_id": None, "file_name": "b.jpg",
         "original_name": "b.jpg", "taken_at": None},
    ]
    measured = [{"id": 3, "local_time": "2026-03-01T10:00:00", "verdict": "failed",
                 "function": "rlo"}]
    gaps = [{"id": 9, "at": "2026-03-01T10:05:00", "seconds": 30.0}]
    data = TimelineData.from_rows(measured, rows, gaps, 5.0, str.upper)
    assert [item.id for item in data.photos] == [1]
    assert data.marks[0].label == "RLO"
    assert data.gaps[0].at == datetime(2026, 3, 1, 10, 5)
    assert to_moment(data.marks[0].at) == T0
