# EasyMeasurement - tests/test_photo_menu_ui.py
# Taking a photo off the timeline, the context menu, and the cards over the window.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import timedelta

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QContextMenuEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from easymeasurement.ui import photo_overlays
from easymeasurement.ui.photo_timeline_events import Hit
from easymeasurement.l10n import tr
from easymeasurement.ui.photo_timeline_mouse import IDLE_HINT

from .photo_ui_helpers import (
    T0,
    centre_of,
    click,
    make_campaign,
    move,
    open_timeline,
    photo_ids,
    press,
    stored_shift,
)


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path)


@pytest.fixture
def timeline(qtbot, app, case):
    return open_timeline(qtbot, app, case[0])


def test_delete_key_sends_the_photo_to_the_stack(qtbot, app, timeline, case):
    view = timeline.view
    photo = photo_ids(app, case[0])[0]
    click(view, centre_of(view, photo))
    with qtbot.waitSignal(timeline.changed):
        QTest.keyClick(view, Qt.Key.Key_Delete)
    assert [row["id"] for row in app.service.stacked_photos(case[0])] == [photo]
    assert photo not in view.photo_items
    assert view.selected is None


def test_delete_key_without_a_selection_does_nothing(timeline, app, case):
    QTest.keyClick(timeline.view, Qt.Key.Key_Delete)
    assert app.service.stacked_photos(case[0]) == []


def test_menu_of_a_timeline_photo(timeline, app, case):
    photo = photo_ids(app, case[0])[0]
    texts = [text for text, _ in timeline.menu_entries(Hit("photo", photo), 0)]
    assert "Vom Messwert lösen" in texts
    assert "Wieder der Zeit folgen" not in texts


def test_menu_of_a_pinned_photo_can_return_it(qtbot, app, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path)
    photo = photo_ids(app, campaign)[0]
    app.service.pin_photo(photo, measured[2])
    timeline = open_timeline(qtbot, app, campaign)
    entries = dict(timeline.menu_entries(Hit("photo", photo), 0))
    with qtbot.waitSignal(timeline.changed):
        entries["Wieder der Zeit folgen"]()
    row = app.service.photos(campaign)[0]
    assert (row["placement"], row["measurement_id"]) == ("timeline", measured[0])


def test_right_click_selects_the_photo_and_opens_its_menu(app, timeline, case):
    view = timeline.view
    seen = []

    def read_and_close():
        menu = QApplication.activePopupWidget()
        seen.append([action.text() for action in menu.actions()])
        menu.close()

    QTimer.singleShot(0, read_and_close)
    photo = photo_ids(app, case[0])[0]
    pos = centre_of(view, photo)
    view.contextMenuEvent(QContextMenuEvent(
        QContextMenuEvent.Reason.Mouse, pos, view.mapToGlobal(pos)
    ))
    assert "Vom Messwert lösen" in seen[0]
    assert view.selected == photo


def test_read_only_menu_only_shows(timeline, app, case):
    timeline.set_read_only(True)
    photo = photo_ids(app, case[0])[0]
    texts = [text for text, _ in timeline.menu_entries(Hit("photo", photo), 0)]
    assert texts == ["Groß anzeigen"]
    assert timeline.menu_entries(Hit("strip"), 0) == []


def test_the_hint_returns_after_a_drag(app, timeline, case):
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    press(view, start)
    move(view, start + QPoint(30, 0))
    QTest.keyClick(view, Qt.Key.Key_Escape)
    assert timeline.hint_label.text() == tr(IDLE_HINT)


def test_double_click_shows_the_photo_large(monkeypatch, app, timeline, case):
    shown = []

    class Fake:
        def __init__(self, title, caption, path, parent, *notes):
            shown.append((title, path.name))

        def exec(self):
            return 0

    monkeypatch.setattr(photo_overlays, "PhotoPreview", Fake)
    view = timeline.view
    photo = photo_ids(app, case[0])[0]
    QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=centre_of(view, photo))
    assert shown and shown[0][0] == "p1.jpg"


def test_the_large_photo_opens_as_a_card(qtbot, window, app, tmp_path):
    source = tmp_path / "big.jpg"
    Image.new("RGB", (640, 480), (20, 120, 60)).save(source)
    card = photo_overlays.PhotoPreview("big.jpg", "Aufgenommen", source, window)
    pixmap = card.canvas.pixmap
    assert not pixmap.isNull()
    assert pixmap.width() <= 640
    card.deleteLater()


def test_start_overlay_sets_the_first_photo(monkeypatch, qtbot, app, timeline, case):
    wanted = T0 + timedelta(minutes=9)

    def answer(overlay):
        overlay.edit.setDateTime(wanted)
        return 1

    monkeypatch.setattr(photo_overlays.PhotoStartOverlay, "exec", answer)
    with qtbot.waitSignal(timeline.changed):
        timeline.start_button.click()
    assert stored_shift(app, case[0]) == 8 * 60
    assert timeline.view.data.first_place() == wanted


def test_keeping_the_start_is_no_change(monkeypatch, app, timeline, case):
    monkeypatch.setattr(photo_overlays.PhotoStartOverlay, "exec", lambda overlay: 1)
    seen = []
    timeline.changed.connect(lambda: seen.append(1))
    timeline.start_button.click()
    assert seen == []


def test_the_cards_really_open_and_close(qtbot, window, tmp_path):
    source = tmp_path / "big.jpg"
    Image.new("RGB", (640, 480), (20, 120, 60)).save(source)
    card = photo_overlays.PhotoPreview("big.jpg", "Aufgenommen", source, window)
    QTimer.singleShot(0, card.ok_button.click)
    assert card.exec() == 1
    card = photo_overlays.PhotoStartOverlay(T0, T0, window)
    QTimer.singleShot(0, card.reject)
    assert card.exec() == 0


def test_start_overlay_offers_the_time_of_the_camera(qtbot, window):
    moved = T0 + timedelta(minutes=9)
    card = photo_overlays.PhotoStartOverlay(moved, T0, window)
    assert card.start == moved
    card.edit.setDateTime(T0)
    assert card.start == T0
    card.deleteLater()


def test_start_without_photos_only_says_so(qtbot, app, asset):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    timeline = open_timeline(qtbot, app, campaign)
    timeline.start_button.click()
    assert "kein Foto" in timeline.hint_label.text()
