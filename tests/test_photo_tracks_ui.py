# OkeyDocu - tests/test_photo_tracks_ui.py
# The tracks on screen: what they show, zoom, pan, reading, closed campaigns.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PIL import Image
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPalette

from okeydocu.model import Verdict
from okeydocu.ui.photo_shared import THUMB_EDGE_PX, read_thumbnail, shared_thumbs
from okeydocu.ui.photo_timeline import PhotoTimeline
from okeydocu.ui.photo_timeline_events import Hit

from .photo_ui_helpers import (
    click,
    drag,
    make_campaign,
    mark_point,
    open_timeline,
    owners,
    photo_ids,
)


EXIF_ORIENTATION = 274


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path)


@pytest.fixture
def timeline(qtbot, app, case):
    return open_timeline(qtbot, app, case[0])


def test_marks_and_thumbnails_are_shown(timeline, case):
    view = timeline.view
    assert set(view.mark_items) == set(case[1])
    assert len(view.photo_items) == 2


def test_each_photo_is_linked_to_its_measurement(timeline, case):
    view = timeline.view
    assert len(view.links.plain) == 2
    first_mark_x = view.axis.x_of(view.data.marks_by_id[case[1][0]].at)
    assert view.links.plain[0].x1() == pytest.approx(first_mark_x)


def test_a_thumbnail_has_its_picture_and_aspect(timeline):
    item = next(iter(timeline.view.photo_items.values()))
    assert item.pixmap is not None
    assert item.width == pytest.approx(item.height * 32 / 24)


def test_a_rotated_photo_stands_upright(app, asset, tmp_path):
    source = tmp_path / "turned.jpg"
    image = Image.new("RGB", (800, 600), (20, 120, 60))
    exif = image.getexif()
    exif[EXIF_ORIENTATION] = 6
    image.save(source, exif=exif)
    pixmap = read_thumbnail(str(source))
    assert pixmap.height() > pixmap.width()
    assert max(pixmap.height(), pixmap.width()) == THUMB_EDGE_PX


def test_an_unreadable_file_still_shows_a_picture(qtbot, app, asset, tmp_path):
    campaign, _ = make_campaign(app, asset, tmp_path)
    row = app.service.photos(campaign)[0]
    app.service.photo_path(campaign, row["file_name"]).write_bytes(b"not a picture")
    shared_thumbs()._pixmaps.clear()
    timeline = open_timeline(qtbot, app, campaign)
    assert timeline.view.photo_items[row["id"]].pixmap is not None


def test_pinned_photo_stands_at_its_measurement_with_its_own_link(qtbot, app, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path)
    photo = photo_ids(app, campaign)[0]
    app.service.pin_photo(photo, measured[2])
    view = open_timeline(qtbot, app, campaign).view
    item = view.photo_items[photo]
    assert item.pos().x() == pytest.approx(view.axis.x_of(view.data.marks_by_id[measured[2]].at))
    assert not item.photo.follows_time
    assert len(view.links.pinned) == 1 and len(view.links.plain) == 1


def test_a_stacked_photo_is_not_on_the_tracks(qtbot, app, asset, tmp_path):
    campaign, _ = make_campaign(app, asset, tmp_path)
    photo = photo_ids(app, campaign)[0]
    app.service.stack_photo(photo)
    assert photo not in open_timeline(qtbot, app, campaign).view.photo_items


def test_clicking_a_mark_tells_the_window(qtbot, timeline, case):
    view = timeline.view
    with qtbot.waitSignal(timeline.measurement_chosen) as signal:
        click(view, mark_point(view, case[1][1]))
    assert signal.args == [case[1][1]]
    assert view.mark_items[case[1][1]].marked


def test_a_measurement_chosen_elsewhere_highlights_its_link(timeline, case):
    timeline.select_measurement(case[1][0])
    assert len(timeline.view.links.strong) == 1


def test_tooltip_of_a_mark_has_time_and_values(timeline, case):
    words = timeline._describe(Hit("mark", case[1][0]))
    assert "2026-03-01  10:00:00" in words
    assert "120\u202fmΩ" in words
    assert "bestanden" in words


def test_tooltip_of_a_photo_says_where_it_belongs(timeline, app, case):
    words = timeline._describe(Hit("photo", photo_ids(app, case[0])[0]))
    assert "p1.jpg" in words and "RLO" in words and "folgt der Zeit" in words


def test_verdict_shows_in_the_shape_as_well(qtbot, app, asset):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    app.service.add_measurement(campaign, "rlo", [], verdict=Verdict.FAILED)
    timeline = open_timeline(qtbot, app, campaign)
    item = next(iter(timeline.view.mark_items.values()))
    assert item.mark.verdict == "failed"
    assert item.zValue() > 0  # failed ones lie on top in a crowded track


def test_shift_is_said_in_plain_words(timeline, app, case):
    app.service.set_photo_shift(case[0], 12)
    timeline.refresh()
    assert timeline.shift_label.text() == "Fotos 12 s später"


# Empty -----------------------------------------------------------------------


def test_an_empty_campaign_says_what_to_do(qtbot, app, asset):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    timeline = open_timeline(qtbot, app, campaign)
    assert all(timeline.view.data.empty_texts())
    image = timeline.view.grab().toImage()
    base = timeline.view.palette().color(QPalette.ColorRole.Base)
    rows = range(timeline.view.tracks.marks_bottom + 2, image.height() - 2)
    strip = [QColor(image.pixel(x, y)) for y in rows for x in range(200, 700, 2)]
    assert any(colour != base for colour in strip)  # the line is really painted


def test_no_campaign_yet_does_no_harm(qtbot, app):
    timeline = PhotoTimeline(app)
    qtbot.addWidget(timeline)
    timeline.refresh()
    timeline.gap_button.click()
    assert "Foto" in timeline.hint_label.text()


# Closed ----------------------------------------------------------------------


def test_read_only_shows_the_same_tracks(qtbot, app, case):
    timeline = open_timeline(qtbot, app, case[0])
    count = len(timeline.view.photo_items)
    timeline.set_read_only(True)
    assert len(timeline.view.photo_items) == count
    assert not timeline.gap_button.isEnabled()
    assert not timeline.start_button.isEnabled()
    assert timeline.fit_button.isEnabled()


def test_a_closed_campaign_locks_itself(qtbot, app, asset, tmp_path):
    campaign, _ = make_campaign(app, asset, tmp_path)
    app.service.close(campaign)
    timeline = open_timeline(qtbot, app, campaign)
    assert timeline.read_only
    assert "nur ansehen" in timeline.hint_label.text()


def test_read_only_still_tells_the_window_about_a_click(qtbot, timeline, case):
    timeline.set_read_only(True)
    view = timeline.view
    with qtbot.waitSignal(timeline.measurement_chosen):
        click(view, mark_point(view, case[1][0]))


def test_read_only_keeps_a_photo_where_it_is(timeline, app, case):
    timeline.set_read_only(True)
    view = timeline.view
    before = owners(app, case[0])
    photo = photo_ids(app, case[0])[0]
    start = view.photo_items[photo].pos().toPoint() + QPoint(4, 20)
    drag(view, start, mark_point(view, case[1][2]))
    drag(view, start, start + QPoint(120, 0))
    assert owners(app, case[0]) == before
    assert app.service.campaign(case[0])["photo_shift_s"] == 0
