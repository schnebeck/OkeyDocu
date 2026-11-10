# EasyMeasurement - tests/test_photo_zoom_ui.py
# Finding one's way along the tracks, and staying fluid with a full campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from easymeasurement.ui.photo_shared import shared_thumbs
from easymeasurement.ui.photo_timeline import PhotoTimeline

from .photo_ui_helpers import (
    T0,
    centre_of,
    drag,
    make_campaign,
    move,
    open_timeline,
    press,
    release,
    wheel,
    write_photo,
)

# Far above what a laptop needs, so a busy test machine cannot fail these.
STEP_LIMIT_S = 0.05
SHOW_LIMIT_S = 1.0


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path)


@pytest.fixture
def timeline(qtbot, app, case):
    return open_timeline(qtbot, app, case[0])


def test_default_view_fits_everything(timeline):
    view = timeline.view
    assert view.fitted
    assert view.axis.shows(*view.data.content_range())


def test_the_fit_follows_the_width(timeline):
    timeline.resize(1200, 190)
    QApplication.processEvents()
    assert timeline.view.axis.width >= 1190
    assert timeline.view.axis.shows(*timeline.view.data.content_range())


def test_wheel_zooms_around_the_pointer(timeline):
    view = timeline.view
    pos = QPoint(400, 80)
    before_scale, before_moment = view.axis.px_per_s, view.axis.seconds_at(400)
    wheel(view, pos, 120)
    assert view.axis.px_per_s > before_scale
    assert view.axis.seconds_at(400) == pytest.approx(before_moment)
    assert not view.fitted


def test_zooming_moves_items_without_rebuilding_them(timeline):
    view = timeline.view
    item = next(iter(view.photo_items.values()))
    x = item.pos().x()
    wheel(view, QPoint(600, 80), 240)
    assert next(iter(view.photo_items.values())) is item
    assert item.pos().x() != x


def test_thumbnails_keep_their_size_when_zooming(timeline):
    view = timeline.view
    item = next(iter(view.photo_items.values()))
    size = item.sceneBoundingRect().size()
    wheel(view, QPoint(600, 80), 480)
    assert item.sceneBoundingRect().size() == size


def test_dragging_empty_space_pans(timeline):
    view = timeline.view
    start = view.axis.start
    y = view.tracks.height - 4
    drag(view, QPoint(780, y), QPoint(700, y))
    assert view.axis.start > start
    assert not view.fitted


def test_fit_button_brings_everything_back(timeline):
    view = timeline.view
    wheel(view, QPoint(400, 80), 960)
    timeline.fit_button.click()
    assert view.fitted
    assert view.axis.shows(*view.data.content_range())


def test_a_refresh_keeps_the_zoom(timeline):
    view = timeline.view
    wheel(view, QPoint(400, 80), 240)
    scale = view.axis.px_per_s
    timeline.refresh()
    assert view.axis.px_per_s == scale


def test_sideways_wheel_cannot_lose_the_content(timeline):
    view = timeline.view
    for _ in range(200):
        wheel(view, QPoint(400, 80), 0, sideways=-4000)
    assert view.axis.x_of(view.data.content_range()[1]) > view.axis.left


def test_a_wide_last_thumbnail_fits_into_the_view(qtbot, app, asset, tmp_path):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    wide = write_photo(tmp_path / "wide.jpg", T0, size=(160, 90))
    app.service.import_photos(campaign, [wide])
    view = open_timeline(qtbot, app, campaign).view
    view.fit()
    item = next(iter(view.photo_items.values()))
    assert item.sceneBoundingRect().right() <= view.axis.width


def test_the_pointer_can_walk_along_a_crowded_deck(qtbot, app, asset, tmp_path):
    """The card under the pointer rises, and still the next one can be reached."""
    campaign, _ = make_campaign(
        app, asset, tmp_path, marks=(0, 60), photos=[n * 0.5 for n in range(40)]
    )
    view = open_timeline(qtbot, app, campaign).view
    items = sorted(view.photo_items.values(), key=lambda item: item.pos().x())
    y = view.tracks.photos_top + 10
    met = []
    for item in items[3:9]:
        move(view, QPoint(round(item.pos().x()) + 1, y))
        met.append(view.hovered)
    assert met == [item.photo.id for item in items[3:9]]


# 150 measurements, 200 photos ------------------------------------------------


@pytest.fixture
def full(qtbot, app, asset, tmp_path):
    campaign, _ = make_campaign(
        app, asset, tmp_path, marks=range(150), photos=[n * 0.75 for n in range(200)]
    )
    return campaign


def test_opening_does_not_wait_for_the_thumbnails(qtbot, app, full):
    shared_thumbs()._pixmaps.clear()
    timeline = PhotoTimeline(app)
    qtbot.addWidget(timeline)
    timeline.resize(860, 190)
    timeline.show()
    started = time.perf_counter()
    timeline.show_campaign(full)
    QApplication.processEvents()
    assert time.perf_counter() - started < SHOW_LIMIT_S
    assert len(timeline.view.photo_items) == 200
    shared_thumbs().finish()


def test_a_shift_step_is_fast_with_painting(qtbot, app, full):
    timeline = open_timeline(qtbot, app, full)
    view = timeline.view
    start = centre_of(view, next(iter(view.photo_items)))
    press(view, start)
    started = time.perf_counter()
    steps = 30
    for step in range(1, steps + 1):
        move(view, start + QPoint(step * 4, 0))
        view.viewport().repaint()
    per_step = (time.perf_counter() - started) / steps
    release(view, start + QPoint(steps * 4, 0))
    assert per_step < STEP_LIMIT_S


def test_a_held_gesture_stops_the_decoding_until_it_ends(qtbot, app, full):
    shared_thumbs()._pixmaps.clear()
    timeline = PhotoTimeline(app)
    qtbot.addWidget(timeline)
    timeline.resize(860, 190)
    timeline.show()
    timeline.show_campaign(full)
    view = timeline.view
    y = view.tracks.height - 4
    press(view, QPoint(400, y))
    waiting = len(shared_thumbs()._waiting)
    assert waiting
    qtbot.wait(40)
    assert len(shared_thumbs()._waiting) == waiting
    release(view, QPoint(400, y))
    qtbot.waitUntil(lambda: len(shared_thumbs()._waiting) < waiting, timeout=2000)
    shared_thumbs().finish()


def test_reading_again_keeps_the_decoded_thumbnails(qtbot, app, full, monkeypatch):
    timeline = open_timeline(qtbot, app, full)
    calls = []
    monkeypatch.setattr("easymeasurement.ui.photo_shared.read_thumbnail",
                        lambda path: calls.append(path))
    timeline.refresh()
    shared_thumbs().finish()
    assert calls == []
