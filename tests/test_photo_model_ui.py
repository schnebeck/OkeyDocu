# OkeyDocu - tests/test_photo_model_ui.py
# The plain logic of the photo timeline: mapping, ticks, wording, drag decisions.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest

from okeydocu.ui.photo_timeline_model import (
    GUTTER_PX,
    MAX_PX_PER_S,
    MIN_GAP_S,
    TimeAxis,
    Tracks,
    Zone,
    default_gap_seconds,
    drag_zone,
    duration_text,
    shift_text,
    stretched_gap,
    tick_step,
    tick_text,
    ticks,
    to_moment,
    to_seconds,
)

from .photo_ui_helpers import T0

TRACKS = Tracks(130)
PHOTO_Y = TRACKS.photos_top + 10
MARK_Y = int(TRACKS.mark_y)


def axis_over(low=0.0, high=3600.0, width=860.0):
    axis = TimeAxis(width)
    axis.fit(low, high)
    return axis


# Mapping ---------------------------------------------------------------------


def test_time_and_pixel_map_onto_each_other():
    axis = axis_over()
    assert axis.seconds_at(axis.x_of(1234.5)) == pytest.approx(1234.5)


def test_seconds_round_trip_through_a_moment():
    assert to_moment(to_seconds(T0)) == T0


def test_fit_shows_all_right_of_the_track_names():
    axis = axis_over(1000, 9000)
    assert axis.x_of(1000) >= GUTTER_PX
    assert axis.x_of(9000) < 860
    assert axis.shows(1000, 9000)


def test_fit_of_one_single_moment_stays_sensible():
    axis = axis_over(500, 500)
    assert axis.px_per_s <= MAX_PX_PER_S
    assert axis.shows(500, 500)


def test_zoom_keeps_the_moment_under_the_pointer():
    axis = axis_over()
    before = axis.seconds_at(300)
    axis.zoom_at(300, 2.0)
    assert axis.seconds_at(300) == pytest.approx(before)


def test_zoom_has_limits_at_both_ends():
    axis = axis_over()
    fitted = axis.px_per_s
    for _ in range(40):
        axis.zoom_at(300, 2.0)
    assert axis.px_per_s == MAX_PX_PER_S
    for _ in range(80):
        axis.zoom_at(300, 0.5)
    assert axis.px_per_s == pytest.approx(fitted / 4)


def test_pan_follows_the_hand():
    axis = axis_over()
    before = axis.x_of(100)
    axis.pan(50)
    assert axis.x_of(100) == pytest.approx(before + 50)


def test_content_cannot_be_panned_out_of_reach():
    axis = axis_over(0, 3600)
    axis.pan(10 ** 7)
    axis.keep_near(0, 3600)
    assert axis.x_of(0) < axis.width
    axis.pan(-(10 ** 8))
    axis.keep_near(0, 3600)
    assert axis.x_of(3600) > axis.left


# Ruler -----------------------------------------------------------------------


@pytest.mark.parametrize("px_per_s, step", [(40, 5), (1, 120), (0.1, 900), (0.001, 86400)])
def test_tick_spacing_fits_the_zoom(px_per_s, step):
    assert tick_step(px_per_s) == step


def test_ticks_fall_on_round_clock_times():
    axis = axis_over(to_seconds(T0), to_seconds(T0) + 3 * 3600)
    labels = [label for _, label in ticks(axis)]
    assert labels and all(label.endswith(("0", "5")) for label in labels)
    assert "11:00" in labels


def test_ticks_stay_right_of_the_track_names():
    axis = axis_over(to_seconds(T0), to_seconds(T0) + 3600)
    assert min(x for x, _ in ticks(axis)) >= axis.left


def test_seconds_appear_only_when_zoomed_in():
    assert tick_text(to_seconds(T0) + 30, 10) == "10:00:30"
    assert tick_text(to_seconds(T0), 600) == "10:00"


def test_midnight_shows_the_date():
    assert tick_text(to_seconds(T0.replace(hour=0)), 3600) == "01.03."


# Words -----------------------------------------------------------------------


@pytest.mark.parametrize("seconds, words", [
    (12, "12 s"), (90, "1 min 30 s"), (120, "2 min"), (3900, "1 h 5 min"), (3600, "1 h"),
    (86400, "1 Tag"), (2 * 86400 + 3 * 3600, "2 Tage 3 h"),
])
def test_durations_read_plainly(seconds, words):
    assert duration_text(seconds) == words


def test_shift_says_later_and_earlier():
    assert shift_text(12) == "Fotos 12 s später"
    assert shift_text(-90) == "Fotos 1 min 30 s früher"
    assert shift_text(0) == "Fotos zur Aufnahmezeit"


# Gaps ------------------------------------------------------------------------


def test_an_inserted_gap_is_visible_at_any_zoom():
    assert default_gap_seconds(10) == 30
    assert default_gap_seconds(0.1) == 900
    assert default_gap_seconds(0.1) * 0.1 >= 80


def test_a_gap_cannot_be_shorter_than_the_minimum():
    assert stretched_gap(60, -10000, 1.0) == MIN_GAP_S
    assert stretched_gap(60, 30, 2.0) == 75


# Drag decisions --------------------------------------------------------------


def zone(x, y, follows=True, can_pin=True):
    return drag_zone(x, y, 800, TRACKS, follows, can_pin)


def test_sideways_in_the_photo_track_moves_all():
    assert zone(300, PHOTO_Y) is Zone.SHIFT


def test_the_links_strip_still_counts_as_sideways():
    assert zone(300, TRACKS.marks_bottom + 1) is Zone.SHIFT


def test_up_among_the_measurements_takes_only_this_photo():
    assert zone(300, MARK_Y) is Zone.PIN


def test_without_measurements_there_is_nothing_to_pin_to():
    assert zone(300, MARK_Y, can_pin=False) is Zone.HOLD


def test_a_pinned_photo_has_no_strip_to_slide_along():
    assert zone(300, PHOTO_Y, follows=False) is Zone.HOLD
    assert zone(300, MARK_Y, follows=False) is Zone.PIN


def test_leaving_up_or_down_hands_the_photo_on():
    assert zone(300, -20) is Zone.LIFT
    assert zone(300, TRACKS.height + 20) is Zone.LIFT


def test_leaving_sideways_keeps_shifting_but_a_lifted_photo_goes():
    assert zone(900, PHOTO_Y) is Zone.SHIFT
    assert zone(900, MARK_Y) is Zone.LIFT
    assert zone(900, PHOTO_Y, follows=False) is Zone.LIFT


# Track bands -----------------------------------------------------------------


def test_thumbnails_take_what_the_height_leaves():
    assert Tracks(130).thumb_height == 130 - Tracks(130).photos_top - 4
    assert Tracks(40).thumb_height == 28
    assert Tracks(600).thumb_height == 110
