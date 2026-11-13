# OkeyDocu - okeydocu/ui/photo_timeline_events.py
# Qt events of the track view: what lies under the pointer, and who gets told.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtWidgets import QToolTip

from .photo_shared import dropped_photo
from .photo_timeline_items import PhotoItem
from .photo_timeline_layers import GapItem, paint_empty_texts, paint_gutter, paint_tracks
from .photo_timeline_model import Tracks

ZOOM_STEP = 1.25
MARK_REACH_PX = 12


@dataclass(frozen=True)
class Hit:
    """What lies under the pointer: photo, mark, gap, gap_grip, gap_close, strip or empty."""

    kind: str
    id: int | None = None


class ViewEvents:
    """The event handlers of the track view, passed on to its `TrackMouse`."""

    def hit(self, pos: QPoint) -> Hit:
        if pos.x() < self.axis.left:
            return Hit("empty")
        # By resting order: a raised card must not hide the neighbours it was lifted over,
        # or the pointer could not walk along a crowded deck.
        under = [item for item in self.items(pos) if isinstance(item, (PhotoItem, GapItem))]
        for item in sorted(under, key=lambda found: found.resting_z, reverse=True):
            if isinstance(item, PhotoItem):
                return Hit("photo", item.photo.id)
            part = item.part_at(item.mapFromScene(QPointF(pos)))
            if part:
                return Hit(part, item.gap_id)
        if pos.y() >= self.tracks.marks_bottom:
            return Hit("strip")
        mark = self.data.nearest_mark(self.axis.seconds_at(pos.x()))
        if pos.y() >= self.tracks.ruler and mark:
            if abs(self.axis.x_of(mark.at) - pos.x()) <= MARK_REACH_PX:
                return Hit("mark", mark.id)
        return Hit("empty")

    def viewportEvent(self, event) -> bool:
        if event.type() == QEvent.Type.ToolTip:  # asked for here, so nothing is prepared ahead
            text = self.describe(self.hit(event.pos()))
            if text:
                QToolTip.showText(event.globalPos(), text, self)
            else:
                QToolTip.hideText()
            return True
        return super().viewportEvent(event)

    def drawBackground(self, painter, rect) -> None:
        paint_tracks(painter, self, rect)

    def drawForeground(self, painter, rect) -> None:
        paint_gutter(painter, self)
        paint_empty_texts(painter, self)

    def mousePressEvent(self, event) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse.press(event.position().toPoint())
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        self.mouse.move(event.position().toPoint())
        event.accept()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouse.release()
        event.accept()

    def mouseDoubleClickEvent(self, event) -> None:
        hit = self.hit(event.position().toPoint())
        if hit.kind == "photo":
            self.photo_opened.emit(hit.id)
        event.accept()

    def leaveEvent(self, event) -> None:
        self.set_hovered(None)
        if self.mouse.gesture is None:
            self.hint.emit(self.mouse.idle_hint())
        super().leaveEvent(event)

    def wheelEvent(self, event) -> None:
        steps = event.angleDelta().y() / 120
        if steps:
            self.axis.zoom_at(event.position().x(), ZOOM_STEP ** steps)
            self.fitted = False
            self.relayout()
        else:
            self.pan_by(event.angleDelta().x() / 2)
        event.accept()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.mouse.cancel()
        elif event.key() == Qt.Key.Key_Delete:
            self.delete_pressed.emit()
        else:
            super().keyPressEvent(event)

    def contextMenuEvent(self, event) -> None:
        hit = self.hit(event.pos())
        if hit.kind == "photo":
            self.set_selected(hit.id)
        self.menu_wanted.emit(hit, self.axis.seconds_at(event.pos().x()), event.globalPos())

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        size = self.viewport().size()
        self.scene().setSceneRect(0, 0, size.width(), size.height())
        self.axis.width = float(size.width())
        self.tracks = Tracks(size.height())
        for item in self.photo_items.values():
            item.set_height(self.tracks.thumb_height)
        if self.fitted:
            self.fit()
        else:
            self.relayout()

    def changeEvent(self, event) -> None:
        if event.type() == QEvent.Type.PaletteChange:
            for item in self.photo_items.values():  # they keep a painted copy for dragging
                item.update()
        super().changeEvent(event)

    def dragEnterEvent(self, event) -> None:
        if not self.read_only and dropped_photo(event.mimeData()) is not None:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        self.mouse.carried_over(event.position().toPoint())
        event.accept()

    def dragLeaveEvent(self, event) -> None:
        self.mouse.carried_away()

    def dropEvent(self, event) -> None:
        photo = dropped_photo(event.mimeData())
        if photo is not None and not self.read_only:
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            self.mouse.carried_in(photo, event.position().toPoint())
