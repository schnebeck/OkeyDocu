# EasyMeasurement - easymeasurement/ui/photo_timeline_layers.py
# The layers around the photos: painted ground of the tracks, gap blocks, links.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainterPath, QPalette, QPen
from PySide6.QtWidgets import QGraphicsItem

from .photo_timeline_items import PIN_COLOUR, palette_of, small_font, soft
from .photo_timeline_model import duration_text, ticks, to_moment

GRIP_PX = 12
CLOSE_PX = 16
MIN_GAP_DRAWN_PX = 16
Role = QPalette.ColorRole


class GapItem(QGraphicsItem):
    """A hatched block in the photo track. Its position is the top left corner."""

    def __init__(self, gap_id: int):
        super().__init__()
        self.gap_id = gap_id
        self.width = float(MIN_GAP_DRAWN_PX)
        self.height = 40.0
        self.seconds = 0.0
        self.editable = True
        self.resting_z = 0.0

    def set_block(self, width: float, height: float, seconds: float) -> None:
        self.prepareGeometryChange()
        self.width = max(width, MIN_GAP_DRAWN_PX)
        self.height = height
        self.seconds = seconds
        self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(-2, -CLOSE_PX - 2, self.width + 4, self.height + CLOSE_PX + 4)

    def close_rect(self) -> QRectF:
        return QRectF(self.width / 2 - CLOSE_PX / 2, -CLOSE_PX - 1, CLOSE_PX, CLOSE_PX)

    def grip_rect(self) -> QRectF:
        return QRectF(self.width - GRIP_PX, 0, GRIP_PX, self.height)

    def part_at(self, point: QPointF) -> str:
        """Which part of the block lies at a point given in item coordinates."""
        if self.editable and self.close_rect().contains(point):
            return "gap_close"
        if self.editable and self.grip_rect().contains(point):
            return "gap_grip"
        return "gap" if QRectF(0, 0, self.width, self.height).contains(point) else ""

    def paint(self, painter, option, widget=None) -> None:
        palette = palette_of(self)
        text = palette.color(QPalette.ColorRole.Text)
        block = QRectF(0, 0, self.width, self.height)
        painter.fillRect(block, palette.color(QPalette.ColorRole.Base))
        painter.fillRect(block, QBrush(soft(text, 110), Qt.BrushStyle.BDiagPattern))
        painter.setPen(QPen(soft(text, 150), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(block)
        words = f"Lücke {duration_text(self.seconds)}"
        painter.setFont(small_font())
        if painter.fontMetrics().horizontalAdvance(words) + 12 < self.width:
            caption = painter.fontMetrics().boundingRect(words).adjusted(-4, -2, 4, 2)
            caption.moveCenter(block.center().toPoint())
            painter.fillRect(caption, palette.color(QPalette.ColorRole.Base))
            painter.setPen(text)
            painter.drawText(block, Qt.AlignmentFlag.AlignCenter, words)
        if self.editable:
            self._paint_controls(painter, palette, text)

    def _paint_controls(self, painter, palette, text: QColor) -> None:
        grip = self.grip_rect()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(palette.color(QPalette.ColorRole.Highlight))
        painter.drawRoundedRect(QRectF(grip.center().x() - 3, 0, 6, self.height), 2, 2)
        painter.setPen(QPen(palette.color(QPalette.ColorRole.HighlightedText), 1))
        for offset in (-5, 0, 5):
            middle = grip.center() + QPointF(0, offset)
            painter.drawLine(middle + QPointF(-1.5, 0), middle + QPointF(1.5, 0))
        close = self.close_rect()
        painter.setPen(QPen(soft(text, 160), 1))
        painter.setBrush(palette.color(QPalette.ColorRole.Base))
        painter.drawEllipse(close)
        painter.setPen(QPen(text, 1.6))
        inner = close.adjusted(5, 5, -5, -5)
        painter.drawLine(inner.topLeft(), inner.bottomRight())
        painter.drawLine(inner.topRight(), inner.bottomLeft())


class LinkLayer(QGraphicsItem):
    """All links in one item: they change on every step of a drag."""

    def __init__(self):
        super().__init__()
        self.plain: list[QLineF] = []
        self.pinned: list[QLineF] = []
        self.strong: list[QLineF] = []
        self.size = QRectF()
        self.setZValue(0.5)

    def set_lines(self, plain, pinned, strong, size: QRectF) -> None:
        self.prepareGeometryChange()
        self.plain, self.pinned, self.strong, self.size = plain, pinned, strong, size
        self.update()

    def boundingRect(self) -> QRectF:
        return self.size

    def shape(self) -> QPainterPath:
        return QPainterPath()

    def paint(self, painter, option, widget=None) -> None:
        palette = palette_of(self)
        painter.setPen(QPen(soft(palette.color(QPalette.ColorRole.Text), 120), 1))
        painter.drawLines(self.plain)
        painter.setPen(QPen(PIN_COLOUR, 1.6))
        painter.drawLines(self.pinned)
        painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight), 2.4))
        painter.drawLines(self.strong)


def paint_tracks(painter, view, rect: QRectF) -> None:
    """The bands and the ruler under all items."""
    palette = view.palette()
    tracks = view.tracks
    width = float(view.viewport().width())
    painter.fillRect(rect, palette.color(Role.Base))
    painter.fillRect(QRectF(0, 0, width, tracks.ruler), palette.color(Role.Window))
    painter.fillRect(
        QRectF(0, tracks.ruler, width, tracks.marks_bottom - tracks.ruler),
        palette.color(Role.AlternateBase),
    )
    text = palette.color(Role.Text)
    painter.setPen(QPen(soft(text, 60), 1))
    painter.drawLine(QLineF(0, tracks.ruler - 0.5, width, tracks.ruler - 0.5))
    painter.drawLine(QLineF(0, tracks.marks_bottom - 0.5, width, tracks.marks_bottom - 0.5))
    painter.setFont(small_font())
    if view.data.content_range():
        _paint_ruler(painter, view, text, palette.color(Role.WindowText))


def _paint_ruler(painter, view, text: QColor, label: QColor) -> None:
    tracks = view.tracks
    bottom = float(view.viewport().height())
    found = ticks(view.axis)
    for x, _ in found:
        painter.setPen(QPen(soft(text, 28), 1))
        painter.drawLine(QLineF(x, tracks.ruler, x, bottom))
        painter.setPen(QPen(soft(text, 120), 1))
        painter.drawLine(QLineF(x, tracks.ruler - 5, x, tracks.ruler))
    painter.setPen(label)
    for x, words in found:
        painter.drawText(QRectF(x + 3, 2, 80, tracks.ruler - 3), Qt.AlignmentFlag.AlignLeft, words)


def paint_gutter(painter, view) -> None:
    """Track names and the date, above the items that pan beneath them."""
    palette = view.palette()
    tracks = view.tracks
    left = view.axis.left
    height = float(view.viewport().height())
    painter.fillRect(QRectF(0, 0, left, height), palette.color(Role.Window))
    painter.setPen(QPen(soft(palette.color(Role.Text), 60), 1))
    painter.drawLine(QLineF(left - 0.5, 0, left - 0.5, height))
    painter.drawLine(QLineF(0, tracks.ruler - 0.5, left, tracks.ruler - 0.5))
    painter.drawLine(QLineF(0, tracks.marks_bottom - 0.5, left, tracks.marks_bottom - 0.5))
    painter.setFont(small_font())
    painter.setPen(palette.color(Role.WindowText))
    flags = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
    if view.data.content_range():
        middle = (view.axis.left + view.axis.width) / 2
        day = to_moment(view.axis.seconds_at(middle)).strftime("%d.%m.%Y")
        painter.drawText(QRectF(6, 0, left - 8, tracks.ruler), flags, day)
    painter.setFont(small_font(bold=True))
    marks_band = QRectF(6, tracks.ruler, left - 8, tracks.marks_bottom - tracks.ruler)
    painter.drawText(marks_band, flags, "Messungen")
    photos_band = QRectF(6, tracks.marks_bottom, left - 8, height - tracks.marks_bottom)
    painter.drawText(photos_band, flags, "Fotos")


def paint_empty_texts(painter, view) -> None:
    """A friendly line in each track that has nothing to show."""
    tracks = view.tracks
    marks_text, photos_text = view.data.empty_texts()
    left = view.axis.left
    width = view.viewport().width() - left
    painter.setFont(small_font())
    painter.setPen(view.palette().color(Role.Text))
    centre = Qt.AlignmentFlag.AlignCenter
    if marks_text:
        band = QRectF(left, tracks.ruler, width, tracks.marks_bottom - tracks.ruler)
        painter.drawText(band, centre, marks_text)
    if photos_text:
        height = view.viewport().height() - tracks.marks_bottom
        painter.drawText(QRectF(left, tracks.marks_bottom, width, height), centre, photos_text)
