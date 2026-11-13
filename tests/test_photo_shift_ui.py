# OkeyDocu - tests/test_photo_shift_ui.py
# Dragging a photo sideways moves all photos on the timeline.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from okeydocu.ui.photo_timeline_model import shift_text

from .photo_ui_helpers import (
    centre_of,
    click,
    drag,
    make_campaign,
    move,
    open_timeline,
    owners,
    photo_ids,
    press,
    release,
    stored_shift,
)


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path)


@pytest.fixture
def timeline(qtbot, app, case):
    return open_timeline(qtbot, app, case[0])


def seconds_for(view, pixels):
    return pixels / view.axis.px_per_s


def test_sideways_moves_all_photos_and_stores_on_release(qtbot, app, timeline, case):
    view = timeline.view
    first, second = photo_ids(app, case[0])
    start = centre_of(view, first)
    other_x = view.photo_items[second].pos().x()
    with qtbot.waitSignal(timeline.changed):
        drag(view, start, start + QPoint(100, 0))
    assert stored_shift(app, case[0]) == pytest.approx(seconds_for(view, 100), abs=1)
    assert view.photo_items[second].pos().x() == pytest.approx(other_x + 100, abs=1)


def test_nothing_is_written_during_the_drag(app, timeline, case):
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    press(view, start)
    move(view, start + QPoint(40, 0))
    move(view, start + QPoint(100, 0))
    assert stored_shift(app, case[0]) == 0
    assert view.data.shift != 0
    release(view, start + QPoint(100, 0))


def test_links_follow_live_and_the_owner_changes(app, timeline, case):
    view = timeline.view
    first, _ = photo_ids(app, case[0])
    start = centre_of(view, first)
    press(view, start)
    distance = round(9 * 60 * view.axis.px_per_s)
    move(view, start + QPoint(distance, 0))
    owner = view.data.owners(view.data.places())[first]
    assert owner == case[1][1]
    assert "wechseln die Messung" in timeline.hint_label.text()
    release(view, start + QPoint(distance, 0))
    assert owners(app, case[0])[0] == case[1][1]


def test_the_scene_is_not_rebuilt_during_a_drag(app, timeline, case):
    view = timeline.view
    items = dict(view.photo_items)
    start = centre_of(view, photo_ids(app, case[0])[0])
    press(view, start)
    for step in range(5, 100, 5):
        move(view, start + QPoint(step, 0))
    assert all(view.photo_items[key] is items[key] for key in items)
    release(view, start)


def test_the_label_says_the_shift_during_the_drag(app, timeline, case):
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    press(view, start)
    move(view, start + QPoint(60, 0))
    assert timeline.shift_label.text() == shift_text(view.data.shift)
    assert "später" in timeline.shift_label.text()
    release(view, start)


def test_a_click_is_not_a_shift(app, timeline, case):
    view = timeline.view
    photo = photo_ids(app, case[0])[0]
    click(view, centre_of(view, photo))
    assert view.selected == photo
    assert stored_shift(app, case[0]) == 0


def test_escape_puts_everything_back(app, timeline, case):
    view = timeline.view
    photo = photo_ids(app, case[0])[0]
    start = centre_of(view, photo)
    x = view.photo_items[photo].pos().x()
    press(view, start)
    move(view, start + QPoint(80, 0))
    QTest.keyClick(view, Qt.Key.Key_Escape)
    release(view, start + QPoint(80, 0))
    assert view.photo_items[photo].pos().x() == pytest.approx(x)
    assert stored_shift(app, case[0]) == 0


def test_a_pinned_photo_does_not_follow(app, qtbot, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path, photos=(1, 11, 15))
    first, second, third = photo_ids(app, campaign)
    app.service.pin_photo(third, measured[0])
    view = open_timeline(qtbot, app, campaign).view
    x = view.photo_items[third].pos().x()
    start = centre_of(view, second)
    drag(view, start, start + QPoint(90, 0))
    assert view.photo_items[third].pos().x() == pytest.approx(x)
    assert stored_shift(app, campaign) != 0
    assert owners(app, campaign)[2] == measured[0]


def test_dragging_near_the_edge_keeps_shifting(qtbot, app, timeline, case):
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    near_edge = QPoint(round(view.axis.width) - 5, start.y())
    press(view, start)
    move(view, near_edge)
    shift = view.data.shift
    assert view.mouse.edge_timer.isActive()
    qtbot.waitUntil(lambda: view.data.shift > shift, timeout=1000)
    release(view, near_edge)
    assert not view.mouse.edge_timer.isActive()
