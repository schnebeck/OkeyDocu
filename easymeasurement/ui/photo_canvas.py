# EasyMeasurement - easymeasurement/ui/photo_canvas.py
# A photo with numbered frames on it; a frame is drawn by dragging across the picture.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..campaign.photo_marks import PhotoMark

MARK = QColor("#e74c3c")
CHOSEN = QColor("#f1c40f")
SMALLEST = 0.01  # a drag shorter than this, as a part of the picture, is a click
BADGE = 11


class MarkCanvas(QWidget):
    """Shows the picture as large as it fits; marks are kept in parts of the picture."""

    drawn = Signal(QRectF)  # a new frame, in fractions of the picture
    chosen = Signal(int)  # the number of the mark clicked

    def __init__(self, pixmap: QPixmap, editable: bool):
        super().__init__()
        self.pixmap = pixmap
        self.editable = editable
        self.marks: list[PhotoMark] = []
        self.current: int | None = None
        self.show_all = True
        self._start: QPointF | None = None
        self._end: QPointF | None = None
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        if editable:
            self.setCursor(Qt.CursorShape.CrossCursor)

    def sizeHint(self) -> QSize:
        return self.pixmap.size() if not self.pixmap.isNull() else QSize(320, 240)

    def picture_rect(self) -> QRectF:
        """Where the picture stands: centred and scaled down to the widget, never up."""
        if self.pixmap.isNull():
            return QRectF()
        size = self.pixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        if size.width() > self.pixmap.width():
            size = self.pixmap.size()
        left = (self.width() - size.width()) / 2
        top = (self.height() - size.height()) / 2
        return QRectF(left, top, size.width(), size.height())

    def _fraction(self, point: QPointF) -> QPointF:
        frame = self.picture_rect()
        x = min(max((point.x() - frame.left()) / frame.width(), 0.0), 1.0)
        y = min(max((point.y() - frame.top()) / frame.height(), 0.0), 1.0)
        return QPointF(x, y)

    def _on_screen(self, mark: PhotoMark) -> QRectF:
        frame = self.picture_rect()
        return QRectF(frame.left() + mark.x * frame.width(), frame.top() + mark.y * frame.height(),
                      mark.w * frame.width(), mark.h * frame.height())

    def mark_at(self, point: QPointF) -> int | None:
        """The smallest shown frame under the point, so a frame inside another can be hit."""
        hits = [m for m in self._shown() if self._on_screen(m).adjusted(-4, -4, 4, 4)
                .contains(point)]
        return min(hits, key=lambda m: m.w * m.h).number if hits else None

    def _shown(self) -> list[PhotoMark]:
        return [m for m in self.marks if self.show_all or m.number == self.current]

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        frame = self.picture_rect()
        if self.pixmap.isNull():
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             "Die Bilddatei lässt sich nicht lesen.")
            return
        painter.drawPixmap(frame.toRect(), self.pixmap)
        font = QFont(self.font())
        font.setBold(True)
        painter.setFont(font)
        for mark in self._shown():
            colour = CHOSEN if mark.number == self.current else MARK
            box = self._on_screen(mark)
            painter.setPen(QPen(colour, 3 if mark.number == self.current else 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(box)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colour)
            painter.drawEllipse(box.topLeft(), BADGE, BADGE)
            painter.setPen(QColor("black") if colour == CHOSEN else QColor("white"))
            badge = QRectF(box.left() - BADGE, box.top() - BADGE, 2 * BADGE, 2 * BADGE)
            painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(mark.number))
        if self._start is not None and self._end is not None:
            painter.setPen(QPen(MARK, 2, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(QRectF(self._start, self._end).normalized())

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = event.position()
        if self.editable and self.picture_rect().contains(point):
            self._start = self._end = point

    def mouseMoveEvent(self, event) -> None:
        if self._start is not None:
            self._end = event.position()
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        point = event.position()
        start, self._start, self._end = self._start, None, None
        self.update()
        if start is not None:
            a, b = self._fraction(start), self._fraction(point)
            box = QRectF(a, b).normalized()
            if box.width() >= SMALLEST and box.height() >= SMALLEST:
                self.drawn.emit(box)
                return
        hit = self.mark_at(point)
        if hit is not None:
            self.chosen.emit(hit)
