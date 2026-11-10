# EasyMeasurement - easymeasurement/ui/status_badges.py
# Show at a glance whether the instrument is connected and its clock is in step.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..campaign.service import ClockState, ClockStatus

ICON_SIZE = 28
MAX_TEXT_WIDTH = 420
GOOD, BAD, WAITING = "good", "bad", "waiting"
_COLOURS = {GOOD: QColor("#2e7d32"), BAD: QColor("#c62828"), WAITING: QColor("#757575")}
_CLOCK_MARKS = {ClockState.SYNCED: GOOD, ClockState.OFFSET: BAD, ClockState.UNKNOWN: WAITING}


def _canvas(ratio: float) -> tuple[QPixmap, QPainter]:
    size = round(ICON_SIZE * ratio)
    pixmap = QPixmap(size, size)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    return pixmap, painter


def _mark(painter: QPainter, kind: str) -> None:
    """The mark in the corner. It, not only the colour, tells the state."""
    badge = QRectF(14, 14, 14, 14)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(_COLOURS[kind])
    painter.drawEllipse(badge)
    white = QColor("white")
    if kind == GOOD:
        pen = QPen(white, 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPolyline([QPointF(17.5, 21), QPointF(20, 23.5), QPointF(24.5, 18)])
    else:
        font = QFont()
        font.setBold(True)
        font.setPixelSize(11)
        painter.setFont(font)
        painter.setPen(white)
        painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, "!" if kind == BAD else "?")


def clock_icon(state: ClockState, face: QColor, ratio: float = 1.0) -> QPixmap:
    pixmap, painter = _canvas(ratio)
    painter.setPen(QPen(face, 2))
    painter.drawEllipse(QRectF(2, 2, 19, 19))
    centre = QPointF(11.5, 11.5)
    painter.drawLine(centre, QPointF(11.5, 6))
    painter.drawLine(centre, QPointF(15.5, 13.5))
    _mark(painter, _CLOCK_MARKS[state])
    painter.end()
    return pixmap


def link_icon(kind: str, face: QColor, ratio: float = 1.0) -> QPixmap:
    """Radio waves from a point."""
    pixmap, painter = _canvas(ratio)
    painter.setPen(QPen(face, 2))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for radius in (6, 11, 16):
        painter.drawArc(QRectF(3 - radius, 21 - radius, 2 * radius, 2 * radius), 0, 90 * 16)
    painter.setBrush(face)
    painter.drawEllipse(QPointF(3, 21), 1.5, 1.5)
    _mark(painter, kind)
    painter.end()
    return pixmap


class _Badge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon = QLabel()
        self.text = QLabel()
        # A long message must wrap: a label would otherwise widen the whole window.
        self.text.setWordWrap(True)
        self.text.setMaximumWidth(MAX_TEXT_WIDTH)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.icon)
        layout.addWidget(self.text)
        self.hide()

    def _face(self) -> QColor:
        return self.palette().color(QPalette.ColorRole.WindowText)

    def _say(self, text: str) -> None:
        """Short messages stay on one line, only long ones wrap."""
        self.text.setText(text)
        width = self.text.fontMetrics().horizontalAdvance(text) + 2
        self.text.setMinimumWidth(min(width, MAX_TEXT_WIDTH))


class LinkBadge(_Badge):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kind: str | None = None

    def show_link(self, kind: str | None, text: str = "") -> None:
        """Without an instrument there is no connection to report on."""
        self.kind = kind
        self.setVisible(kind is not None)
        if kind is not None:
            self.icon.setPixmap(link_icon(kind, self._face(), self.devicePixelRatioF()))
            self._say(text)


class ClockBadge(_Badge):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.state: ClockState | None = None

    def show_status(self, status: ClockStatus | None) -> None:
        """Shown only when the clock asks for attention: not checked, or off. A clock in step
        is the normal case and says nothing."""
        self.state = status.state if status else None
        self.setVisible(status is not None and status.state is not ClockState.SYNCED)
        if status is None:
            return
        self.icon.setPixmap(clock_icon(status.state, self._face(), self.devicePixelRatioF()))
        self._say(status.text)
        self.setToolTip(status.text)
