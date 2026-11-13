# OkeyDocu - tests/test_photo_gaps_ui.py
# Gaps in the photo track: insert, stretch, remove.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import timedelta

import pytest
from PySide6.QtCore import QPoint

from okeydocu.ui.photo_timeline_events import Hit
from okeydocu.ui.photo_timeline_model import MIN_GAP_S, to_seconds

from .photo_ui_helpers import (
    T0,
    centre_of,
    click,
    drag,
    make_campaign,
    move,
    open_timeline,
    photo_ids,
    press,
    release,
)


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path, photos=(1, 11, 15))


@pytest.fixture
def gapped(app, case):
    app.service.add_photo_gap(case[0], T0 + timedelta(minutes=5), 180)
    return case


@pytest.fixture
def timeline(qtbot, app, gapped):
    return open_timeline(qtbot, app, gapped[0])


def only_gap(app, campaign):
    (row,) = app.service.photo_gaps(campaign)
    return row


def grip_of(view, gap_id):
    item = view.gap_items[gap_id]
    return item.mapToScene(item.grip_rect().center()).toPoint()


def test_the_toolbar_inserts_before_the_selected_photo(qtbot, app, case):
    timeline = open_timeline(qtbot, app, case[0])
    view = timeline.view
    second = photo_ids(app, case[0])[1]
    click(view, centre_of(view, second))
    with qtbot.waitSignal(timeline.changed):
        timeline.gap_button.click()
    row = only_gap(app, case[0])
    assert row["at"] == (T0 + timedelta(minutes=11)).isoformat()
    assert view.data.places()[second] > to_seconds(T0 + timedelta(minutes=11))


def test_the_toolbar_without_a_selection_says_what_to_do(qtbot, app, case):
    timeline = open_timeline(qtbot, app, case[0])
    timeline.gap_button.click()
    assert app.service.photo_gaps(case[0]) == []
    assert "anklicken" in timeline.hint_label.text()


def test_right_click_inserts_where_the_pointer_is(qtbot, app, case):
    timeline = open_timeline(qtbot, app, case[0])
    place = to_seconds(T0 + timedelta(minutes=5))
    entries = dict(timeline.menu_entries(Hit("strip"), place))
    with qtbot.waitSignal(timeline.changed):
        entries["Lücke hier einfügen"]()
    assert only_gap(app, case[0])["at"] == (T0 + timedelta(minutes=5)).isoformat()


def test_right_click_behind_a_gap_finds_the_time_of_taking(app, timeline, gapped):
    place = to_seconds(T0 + timedelta(minutes=20))
    entries = dict(timeline.menu_entries(Hit("strip"), place))
    entries["Lücke hier einfügen"]()
    moments = [row["at"] for row in app.service.photo_gaps(gapped[0])]
    assert (T0 + timedelta(minutes=17)).isoformat() in moments


def test_a_gap_moves_the_photos_after_it(timeline, app, gapped):
    second = photo_ids(app, gapped[0])[1]
    assert timeline.view.data.places()[second] == to_seconds(T0 + timedelta(minutes=14))


def test_an_inserted_gap_can_be_seen_at_this_zoom(qtbot, app, case):
    timeline = open_timeline(qtbot, app, case[0])
    view = timeline.view
    click(view, centre_of(view, photo_ids(app, case[0])[1]))
    timeline.gap_button.click()
    assert only_gap(app, case[0])["seconds"] * view.axis.px_per_s >= 40


def test_the_grip_stretches_the_gap_on_release(qtbot, app, timeline, gapped):
    view = timeline.view
    gap_id = only_gap(app, gapped[0])["id"]
    grip = grip_of(view, gap_id)
    with qtbot.waitSignal(timeline.changed):
        drag(view, grip, grip + QPoint(60, 0))
    wanted = 180 + 60 / view.axis.px_per_s
    assert only_gap(app, gapped[0])["seconds"] == pytest.approx(wanted, abs=1)
    assert only_gap(app, gapped[0])["at"] == (T0 + timedelta(minutes=5)).isoformat()


def test_photos_follow_the_grip_live_and_nothing_is_written(app, timeline, gapped):
    view = timeline.view
    gap_id = only_gap(app, gapped[0])["id"]
    second = photo_ids(app, gapped[0])[1]
    x = view.photo_items[second].pos().x()
    grip = grip_of(view, gap_id)
    press(view, grip)
    move(view, grip + QPoint(50, 0))
    assert view.photo_items[second].pos().x() == pytest.approx(x + 50, abs=1)
    assert only_gap(app, gapped[0])["seconds"] == 180
    assert "Lücke" in timeline.hint_label.text()
    release(view, grip + QPoint(50, 0))


def test_a_gap_cannot_be_pulled_shorter_than_the_minimum(app, timeline, gapped):
    view = timeline.view
    grip = grip_of(view, only_gap(app, gapped[0])["id"])
    drag(view, grip, QPoint(view.axis.left + 1, grip.y()))
    assert only_gap(app, gapped[0])["seconds"] == MIN_GAP_S


def test_the_close_button_removes_the_gap(qtbot, app, timeline, gapped):
    view = timeline.view
    item = view.gap_items[only_gap(app, gapped[0])["id"]]
    second = photo_ids(app, gapped[0])[1]
    with qtbot.waitSignal(timeline.changed):
        click(view, item.mapToScene(item.close_rect().center()).toPoint())
    assert app.service.photo_gaps(gapped[0]) == []
    assert view.data.places()[second] == to_seconds(T0 + timedelta(minutes=11))


def test_the_gap_menu_removes_it_too(app, timeline, gapped):
    gap_id = only_gap(app, gapped[0])["id"]
    entries = dict(timeline.menu_entries(Hit("gap", gap_id), 0))
    entries["Lücke entfernen"]()
    assert app.service.photo_gaps(gapped[0]) == []


def test_read_only_keeps_gaps_and_takes_their_handles(app, timeline, gapped):
    gap_id = only_gap(app, gapped[0])["id"]
    timeline.set_read_only(True)
    view = timeline.view
    item = view.gap_items[gap_id]
    assert item.part_at(item.grip_rect().center()) == "gap"
    assert item.part_at(item.close_rect().center()) == ""
    click(view, item.mapToScene(item.close_rect().center()).toPoint())
    assert len(app.service.photo_gaps(gapped[0])) == 1
    assert timeline.menu_entries(Hit("gap", gap_id), 0) == []
