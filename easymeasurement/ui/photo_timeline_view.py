# EasyMeasurement - easymeasurement/ui/photo_timeline_view.py
# The graphics view of the tracks. Items are built once per reading of the data.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QFrame, QGraphicsScene, QGraphicsView

from .photo_shared import ThumbCache
from .photo_timeline_data import TimelineData
from .photo_timeline_events import Hit, ViewEvents
from .photo_timeline_items import MarkItem, PhotoItem
from .photo_timeline_layers import GapItem, LinkLayer
from .photo_timeline_model import TimeAxis, Tracks
from .photo_timeline_mouse import TrackMouse
from .photo_timeline_placing import Z_GAP, Z_PINNED, Z_TIMELINE, TrackPlacing

PIN_FAN_PX = 16  # photos pinned to one measurement stand side by side like cards
WIDEST_RATIO = 16 / 9  # the last thumbnail reaches this far right of its moment


class TrackView(ViewEvents, TrackPlacing, QGraphicsView):
    hint = Signal(str)
    shift_moved = Signal(float)
    shift_done = Signal(float)
    pin_done = Signal(int, int)
    photo_returned = Signal(int)
    gap_resized = Signal(int, float)
    gap_closed = Signal(int)
    mark_clicked = Signal(int)
    photo_opened = Signal(int)
    delete_pressed = Signal()
    selection_changed = Signal()
    menu_wanted = Signal(object, float, QPoint)
    axis_moved = Signal()  # after any zoom, pan, fit or resize

    def __init__(self, thumbs: ThumbCache):
        super().__init__()
        self.thumbs = thumbs
        self.data = TimelineData([], [], [])
        self.axis = TimeAxis()
        self.tracks = Tracks(120)
        self.read_only = False
        self.fitted = True
        self.selected: int | None = None
        self.hovered: int | None = None
        self.chosen_mark: int | None = None
        self.target_mark: int | None = None
        self.floating: tuple[int, float, float] | None = None
        self.describe: Callable[[Hit], str] = lambda hit: ""
        self.photo_items: dict[int, PhotoItem] = {}
        self.mark_items: dict[int, MarkItem] = {}
        self.gap_items: dict[int, GapItem] = {}
        self.fan: dict[int, float] = {}
        self._by_path: dict[str, list[PhotoItem]] = {}
        self.mouse = TrackMouse(self)
        canvas = QGraphicsScene(self)
        canvas.setItemIndexMethod(QGraphicsScene.ItemIndexMethod.NoIndex)
        self.setScene(canvas)
        self.links = LinkLayer()
        canvas.addItem(self.links)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.viewport().setMouseTracking(True)
        self.setAcceptDrops(True)
        self.setMinimumHeight(100)
        thumbs.ready.connect(self._thumb_ready)

    def show_data(self, data: TimelineData, paths: dict[int, Path]) -> None:
        self.mouse.cancel()
        self.data = data
        canvas = self.scene()
        canvas.clear()
        self.links = LinkLayer()
        canvas.addItem(self.links)
        self.mark_items = {mark.id: MarkItem(mark, self.tracks.label) for mark in data.marks}
        self.gap_items = {gap.id: GapItem(gap.id) for gap in data.gaps}
        self._build_photos(paths)
        for item in (*self.mark_items.values(), *self.photo_items.values()):
            canvas.addItem(item)
        for item in self.gap_items.values():
            item.resting_z = Z_GAP
            item.setZValue(Z_GAP)
            item.editable = not self.read_only
            canvas.addItem(item)
        self.hovered = None
        if self.chosen_mark not in self.mark_items:
            self.chosen_mark = None
        content = data.content_range()
        if self.fitted and content and not self.axis.shows(*content):
            self.fit()
        else:
            self.relayout()

    def _build_photos(self, paths: dict[int, Path]) -> None:
        self.photo_items, self._by_path, self.fan = {}, {}, {}
        ranks: dict[int, list[int]] = {}
        places = self.data.places()
        in_time = sorted(places, key=lambda photo_id: (places[photo_id], photo_id))
        rank_of = {photo_id: rank for rank, photo_id in enumerate(in_time)}
        for photo in self.data.photos:
            item = PhotoItem(photo, self.tracks.thumb_height)
            item.set_pixmap(self.thumbs.get(paths[photo.id]))
            base = Z_TIMELINE if photo.follows_time else Z_PINNED
            item.resting_z = base + rank_of.get(photo.id, 0)
            item.setZValue(item.resting_z)
            self.photo_items[photo.id] = item
            self._by_path.setdefault(str(paths[photo.id]), []).append(item)
            if not photo.follows_time:
                ranks.setdefault(photo.owner, []).append(photo.id)
        for pinned in ranks.values():
            for rank, photo_id in enumerate(pinned):
                self.fan[photo_id] = rank * PIN_FAN_PX
        if self.selected in self.photo_items:
            self._restack(self.selected)
        else:
            self.selected = None

    def _thumb_ready(self, path: str) -> None:
        for item in self._by_path.get(path, ()):
            item.set_pixmap(self.thumbs.get(Path(path)))

    def relayout(self) -> None:
        super().relayout()
        self.axis_moved.emit()

    def fit(self) -> None:
        self.fitted = True
        content = self.data.content_range()
        if content:
            self.axis.fit(*content, right=self.tracks.thumb_height * WIDEST_RATIO + 8)
        self.relayout()

    def pan_by(self, dx: float) -> None:
        self.axis.pan(dx)
        content = self.data.content_range()
        if content:
            self.axis.keep_near(*content)
        self.fitted = False
        self.relayout()

    def set_read_only(self, read_only: bool) -> None:
        self.read_only = read_only
        self.mouse.cancel()
        for item in self.gap_items.values():
            item.editable = not read_only
            item.update()
        self.viewport().unsetCursor()
