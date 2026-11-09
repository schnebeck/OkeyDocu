# EasyMeasurement - easymeasurement/ui/photo_timeline_placing.py
# Puts the items of the track view where the axis says, and keeps their stacking order.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QLineF, QRectF
from PySide6.QtGui import QFontMetricsF

from ..model import Verdict
from .photo_timeline_items import MARK_PX, small_font

MIN_MARK_PX = 6.0
LABEL_ROOM_PX = 18  # a mark closer to its neighbour than this keeps its name in the tooltip
LABEL_GAP_PX = 8
Z_GAP, Z_SELECTED, Z_HOVERED, Z_FLOATING = 2500, 4000, 5000, 6000
Z_TIMELINE, Z_PINNED = 1000, 3000  # plus the rank in time, so later photos lie on top


def mark_size(xs: list[float]) -> float:
    """Marks shrink when many share the view, so each stays a separate shape."""
    if len(xs) < 2:
        return float(MARK_PX)
    return min(max((xs[-1] - xs[0]) / (len(xs) - 1), MIN_MARK_PX), float(MARK_PX))


def label_slots(view) -> set[int]:
    """The marks with room for their name. Failed ones get theirs first."""
    axis = view.axis
    metrics = QFontMetricsF(small_font())
    xs = [axis.x_of(mark.at) for mark in view.data.marks]
    roomy = []
    for index, mark in enumerate(view.data.marks):
        before = xs[index] - xs[index - 1] if index else LABEL_ROOM_PX
        after = xs[index + 1] - xs[index] if index + 1 < len(xs) else LABEL_ROOM_PX
        if min(before, after) >= LABEL_ROOM_PX and axis.left <= xs[index] <= axis.width:
            roomy.append((mark.verdict != Verdict.FAILED.value, xs[index], mark))
    taken: list[tuple[float, float]] = []
    chosen = set()
    for _, x, mark in sorted(roomy, key=lambda entry: entry[:2]):
        half = metrics.horizontalAdvance(mark.label) / 2 + LABEL_GAP_PX / 2
        if all(x + half <= left or x - half >= right for left, right in taken):
            taken.append((x - half, x + half))
            chosen.add(mark.id)
    return chosen


class TrackPlacing:
    """The placing half of the track view."""

    def relayout(self) -> None:
        """Place everything after a change of zoom, pan or size."""
        y = self.tracks.mark_y
        slots = label_slots(self)
        axis = self.axis
        visible = [
            x for x in (axis.x_of(mark.at) for mark in self.data.marks)
            if axis.left <= x <= axis.width
        ]
        size = mark_size(visible)
        for mark_id, item in self.mark_items.items():
            item.setPos(axis.x_of(item.mark.at), y)
            item.set_size(size)
            item.show_label = mark_id in slots
            item.set_marked(mark_id in (self.chosen_mark, self.target_mark))
            item.update()
        self.place_photos()
        self.viewport().update()

    def place_photos(self) -> None:
        """Move photos, gaps and links. This is all a step of a drag costs."""
        data, axis, tracks = self.data, self.axis, self.tracks
        places = data.places()
        owners = data.owners(places)
        plain, pinned, strong = [], [], []
        link_top = tracks.mark_y + MARK_PX / 2 + 1
        floating = self.floating[0] if self.floating else None
        for photo_id, item in self.photo_items.items():
            if photo_id not in places:
                item.hide()
                continue
            x = axis.x_of(places[photo_id]) + self.fan.get(photo_id, 0.0)
            y = float(tracks.photos_top)
            owner = owners[photo_id]
            if photo_id == floating:
                x, y = self.floating[1] - item.width / 2, self.floating[2]
                owner = self.target_mark if self.target_mark is not None else owner
            item.setPos(x, y)
            mark = data.marks_by_id.get(owner)
            if mark is None:
                continue
            mark_x = axis.x_of(mark.at)
            if max(mark_x, x) < axis.left or min(mark_x, x) > axis.width:
                continue
            line = QLineF(mark_x, link_top, x + 1, y)
            if photo_id in (self.selected, self.hovered) or owner == self.chosen_mark:
                strong.append(line)
            elif item.photo.follows_time:
                plain.append(line)
            else:
                pinned.append(line)
        self.links.set_lines(plain, pinned, strong, QRectF(self.viewport().rect()))
        spans = data.gap_spans()
        for gap in data.gaps:
            start, end = spans[gap.id]
            item = self.gap_items[gap.id]
            item.setPos(axis.x_of(start), tracks.photos_top)
            item.set_block(axis.x_of(end) - axis.x_of(start), tracks.thumb_height, gap.seconds)

    def _restack(self, photo_id: int) -> None:
        item = self.photo_items[photo_id]
        item.set_selected(photo_id == self.selected)
        item.setZValue(Z_SELECTED if photo_id == self.selected else item.resting_z)

    def set_selected(self, photo_id: int | None) -> None:
        before, self.selected = self.selected, photo_id
        for known in (before, photo_id):
            if known in self.photo_items:
                self._restack(known)
        if photo_id != before:
            self.selection_changed.emit()
        self.place_photos()

    def set_hovered(self, photo_id: int | None) -> None:
        if photo_id == self.hovered:
            return
        before, self.hovered = self.hovered, photo_id
        if before in self.photo_items:
            self._restack(before)
        if photo_id in self.photo_items:
            self.photo_items[photo_id].setZValue(Z_HOVERED)
        self.place_photos()

    def set_float(self, photo_id: int | None, x: float = 0.0, y: float = 0.0) -> None:
        """Let a thumbnail follow the pointer on its own, the others stay as they are."""
        if self.floating and self.floating[0] != photo_id:
            item = self.photo_items[self.floating[0]]
            item.setOpacity(1.0)
            self._restack(self.floating[0])
        self.floating = None if photo_id is None else (photo_id, x, y)
        if photo_id is not None:
            item = self.photo_items[photo_id]
            item.setOpacity(0.85)
            item.setZValue(Z_FLOATING)

    def set_target(self, mark_id: int | None) -> None:
        if mark_id != self.target_mark:
            self.target_mark = mark_id
            for item in self.mark_items.values():
                item.set_marked(item.mark.id in (self.chosen_mark, mark_id))

    def choose_mark(self, mark_id: int | None) -> None:
        self.chosen_mark = mark_id
        for item in self.mark_items.values():
            item.set_marked(item.mark.id in (mark_id, self.target_mark))
        self.place_photos()
