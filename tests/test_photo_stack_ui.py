# EasyMeasurement - tests/test_photo_stack_ui.py
# The stack of unassigned photos, and carrying photos between widgets.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from easymeasurement.ui import photo_stack

from .photo_ui_helpers import make_campaign, open_stack, owners, photo_ids, write_photo

YES, NO = QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No


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


def choose(stack, *rows):
    stack.list.clearSelection()
    for row in rows:
        stack.list.item(row).setSelected(True)


def answer_with(monkeypatch, answer):
    asked = []

    def question(*args):
        asked.append(args)
        return answer

    monkeypatch.setattr(QMessageBox, "question", question)
    return asked


def test_count_is_for_the_section_title(stack):
    assert stack.count == 2


def test_thumbnails_arrive(stack):
    assert not stack.list.item(0).icon().isNull()


def test_an_empty_stack_still_has_something_to_say(qtbot, app, case):
    stack = open_stack(qtbot, app, case[0])
    assert stack.count == 0
    assert not stack.back_button.isEnabled() and not stack.delete_button.isEnabled()
    stack.list.grab()  # paints its line instead of a blank box


def test_back_on_the_timeline_by_button(qtbot, app, stack, stacked):
    choose(stack, 0, 1)
    with qtbot.waitSignal(stack.changed):
        stack.back_button.click()
    assert stack.count == 0
    assert owners(app, stacked[0]) == stacked[1][:2]


def test_a_photo_without_a_time_cannot_go_back_by_button(qtbot, app, stacked, tmp_path):
    app.service.import_photos(stacked[0], [write_photo(tmp_path / "x.png")])
    stack = open_stack(qtbot, app, stacked[0])
    row = next(i for i in range(stack.count) if stack.list.item(i).text() == "ohne Zeit")
    choose(stack, row)
    assert not stack.back_button.isEnabled()
    assert "Ziehen" in stack.hint.text()


def test_deleting_asks_and_no_keeps_the_photo(monkeypatch, app, stack, stacked):
    asked = answer_with(monkeypatch, NO)
    choose(stack, 0)
    stack.delete_button.click()
    assert len(asked) == 1
    assert "p1.jpg" in asked[0][2]
    assert len(app.service.photos(stacked[0])) == 2


def test_yes_deletes_photo_and_file(monkeypatch, qtbot, app, stack, stacked):
    answer_with(monkeypatch, YES)
    row = app.service.photos(stacked[0])[0]
    path = app.service.photo_path(stacked[0], row["file_name"])
    choose(stack, 0)
    with qtbot.waitSignal(stack.changed):
        stack.delete_button.click()
    assert not path.exists()
    assert stack.count == 1


def test_several_photos_are_asked_for_at_once(monkeypatch, app, stack, stacked):
    asked = answer_with(monkeypatch, YES)
    choose(stack, 0, 1)
    stack.delete_button.click()
    assert len(asked) == 1 and "2 Fotos" in asked[0][2]
    assert app.service.photos(stacked[0]) == []


def test_read_only_changes_nothing(monkeypatch, app, stack, stacked):
    asked = answer_with(monkeypatch, YES)
    stack.set_read_only(True)
    choose(stack, 0)
    assert not stack.back_button.isEnabled()
    assert not stack.delete_button.isEnabled()
    stack.delete_selected()
    stack.put_back()
    assert asked == []
    assert stack.count == 2
    assert not stack.list.dragEnabled()


def test_a_closed_campaign_locks_the_stack(qtbot, app, stacked):
    app.service.close(stacked[0])
    assert open_stack(qtbot, app, stacked[0]).read_only


def test_dragging_starts_with_the_photo_id(monkeypatch, app, stack, stacked):
    carried = []
    monkeypatch.setattr(photo_stack, "start_photo_drag",
                        lambda _, photo, pixmap: carried.append(photo))
    stack.list.setCurrentRow(1)
    stack.list.startDrag(Qt.DropAction.MoveAction)
    assert carried == [photo_ids(app, stacked[0])[1]]


def test_delete_key_asks_too(monkeypatch, app, stack, stacked):
    asked = answer_with(monkeypatch, NO)
    choose(stack, 0)
    QTest.keyClick(stack, Qt.Key.Key_Delete)
    assert len(asked) == 1
    assert len(app.service.photos(stacked[0])) == 2


def test_double_click_shows_the_photo_large(monkeypatch, stack):
    shown = []

    class Fake:
        def __init__(self, title, caption, path, parent, *notes):
            shown.append(title)

        def exec(self):
            return 0

    monkeypatch.setattr(photo_stack, "PhotoPreview", Fake)
    stack.list.itemDoubleClicked.emit(stack.list.item(0))
    assert shown == ["p1.jpg"]


def test_the_selection_survives_reading_again(stack):
    choose(stack, 1)
    stack.refresh()
    assert [item.text() for item in stack.list.selectedItems()] == [stack.list.item(1).text()]
