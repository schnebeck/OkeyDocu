# EasyMeasurement - tests/test_photo_carry_ui.py
# Carrying a photo between the timeline, the stack and other widgets.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PySide6.QtCore import QMimeData, QPoint
from PySide6.QtWidgets import QTableWidget

from easymeasurement.ui import photo_shared
from easymeasurement.ui.photo_shared import (
    PHOTO_MIME,
    accept_photo_drops,
    dropped_photo,
    photo_mime_data,
)

from .photo_ui_helpers import (
    carry_over,
    drop_on,
    make_campaign,
    mark_point,
    open_stack,
    open_timeline,
    owners,
    photo_ids,
    write_photo,
)


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path)


@pytest.fixture
def stacked(app, case):
    """Both photos on the stack."""
    for photo in photo_ids(app, case[0]):
        app.service.stack_photo(photo)
    return case


@pytest.fixture
def stack(qtbot, app, stacked):
    return open_stack(qtbot, app, stacked[0])


def test_the_mime_data_holds_the_id():
    assert dropped_photo(photo_mime_data(42)) == 42


def test_other_drags_are_no_photo():
    mime = QMimeData()
    mime.setText("42")
    assert dropped_photo(mime) is None
    mime.setData(PHOTO_MIME, b"nonsense")
    assert dropped_photo(mime) is None


def test_a_table_can_take_a_photo(qtbot):
    table = QTableWidget(3, 2)
    qtbot.addWidget(table)
    table.show()
    got = []
    accept_photo_drops(table.viewport(), lambda photo, pos: got.append((photo, pos)))
    event = drop_on(table.viewport(), photo_mime_data(7), QPoint(12, 14))
    assert got == [(7, QPoint(12, 14))]
    assert event.isAccepted()


def test_a_target_can_refuse_a_position(qtbot):
    table = QTableWidget(3, 2)
    qtbot.addWidget(table)
    got = []
    accept_photo_drops(table.viewport(), lambda *args: got.append(args), lambda pos: False)
    drop_on(table.viewport(), photo_mime_data(7))
    assert got == []


def test_a_target_ignores_other_drags(qtbot):
    table = QTableWidget(3, 2)
    qtbot.addWidget(table)
    got = []
    accept_photo_drops(table.viewport(), lambda *args: got.append(args))
    mime = QMimeData()
    mime.setText("7")
    drop_on(table.viewport(), mime)
    assert got == []


def test_a_timeline_photo_dropped_on_the_stack_loses_its_assignment(qtbot, app, case):
    stack = open_stack(qtbot, app, case[0])
    photo = photo_ids(app, case[0])[0]
    with qtbot.waitSignal(stack.changed):
        drop_on(stack.list.viewport(), photo_mime_data(photo))
    assert stack.count == 1
    assert owners(app, case[0])[0] is None


def test_a_stack_photo_dropped_on_itself_changes_nothing(qtbot, app, stack, stacked):
    seen = []
    stack.changed.connect(lambda: seen.append(1))
    drop_on(stack.list.viewport(), photo_mime_data(photo_ids(app, stacked[0])[0]))
    assert seen == []


def test_a_stack_photo_dropped_on_a_mark_is_pinned(qtbot, app, stacked):
    timeline = open_timeline(qtbot, app, stacked[0])
    view = timeline.view
    photo = photo_ids(app, stacked[0])[0]
    with qtbot.waitSignal(timeline.changed):
        carry_over(view, photo, mark_point(view, stacked[1][2]))
    row = app.service.photos(stacked[0])[0]
    assert (row["placement"], row["measurement_id"]) == ("pinned", stacked[1][2])


def test_a_stack_photo_dropped_in_the_strip_returns_to_its_time(qtbot, app, stacked):
    timeline = open_timeline(qtbot, app, stacked[0])
    view = timeline.view
    photo = photo_ids(app, stacked[0])[0]
    with qtbot.waitSignal(timeline.changed):
        carry_over(view, photo, QPoint(400, view.tracks.photos_top + 10))
    assert app.service.photos(stacked[0])[0]["placement"] == "timeline"


def test_a_photo_without_a_time_in_the_strip_gets_an_answer(qtbot, app, stacked, tmp_path):
    app.service.import_photos(stacked[0], [write_photo(tmp_path / "x.png")])
    photo = app.service.stacked_photos(stacked[0])[0]["id"]  # without a time it sorts first
    timeline = open_timeline(qtbot, app, stacked[0])
    view = timeline.view
    carry_over(view, photo, QPoint(400, view.tracks.photos_top + 10))
    assert "keine Aufnahmezeit" in timeline.hint_label.text()


def test_the_shared_cache_is_one(qtbot):
    assert photo_shared.shared_thumbs() is photo_shared.shared_thumbs()
