# EasyMeasurement - easymeasurement/ui/photo_timeline_items.py
# The thumbnails and the measurement marks on the tracks.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPalette, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QGraphicsItem

from ..model import Verdict
from .photo_timeline_data import TrackMark, TrackPhoto

PIN_COLOUR = QColor("#e67e22")
VERDICT_COLOURS = {
    Verdict.PASSED.value: QColor("#2e7d32"),
    Verdict.FAILED.value: QColor("#d32f2f"),
    Verdict.NOT_EVALUATED.value: QColor("#7a8087"),
}
RATIO_WITHOUT_PICTURE = 4 / 3
MARK_PX = 12
LABEL_FONT_PX = 11


def small_font(bold: bool = False) -> QFont:
    font = QFont()
    font.setPixelSize(LABEL_FONT_PX)
    font.setBold(bold)
    return font


def palette_of(item: QGraphicsItem) -> QPalette:
    """The palette of the view: a scene would only know the application's."""
    return item.scene().views()[0].palette()


def soft(colour: QColor, alpha: int) -> QColor:
    faded = QColor(colour)
    faded.setAlpha(alpha)
    return faded


class PhotoItem(QGraphicsItem):
    """A thumbnail. Like a clip it starts at its moment: the position is its top left corner.

    Later photos lie on earlier ones, so in a crowded view the strip left visible of
    each one stands exactly at its moment, where its link ends.
    """

    def __init__(self, photo: TrackPhoto, height: int):
        super().__init__()
        self.photo = photo
        self.height = height
        self.pixmap: QPixmap | None = None
        self.selected = False
        self.resting_z = 0.0
        self.setCacheMode(QGraphicsItem.CacheMode.DeviceCoordinateCache)

    @property
    def width(self) -> float:
        if self.pixmap is None:
            return self.height * RATIO_WITHOUT_PICTURE
        return self.height * self.pixmap.width() / max(self.pixmap.height(), 1)

    def set_pixmap(self, pixmap: QPixmap | None) -> None:
        self.prepareGeometryChange()
        self.pixmap = pixmap
        self.update()

    def set_height(self, height: int) -> None:
        self.prepareGeometryChange()
        self.height = height

    def set_selected(self, selected: bool) -> None:
        if selected != self.selected:
            self.selected = selected
            self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(-3, -7, self.width + 10, self.height + 10)

    def paint(self, painter, option, widget=None) -> None:
        palette = palette_of(self)
        rect = QRectF(0, 0, self.width, self.height)
        if self.pixmap is None:
            painter.fillRect(rect, palette.color(QPalette.ColorRole.Mid))
        else:
            painter.drawPixmap(rect, self.pixmap, QRectF(self.pixmap.rect()))
        pinned = not self.photo.follows_time
        if self.selected:
            painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight), 3))
        elif pinned:
            painter.setPen(QPen(PIN_COLOUR, 2))
        else:
            painter.setPen(QPen(palette.color(QPalette.ColorRole.Base), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(rect)
        if pinned:
            self._paint_pin(painter, QPointF(rect.right() - 2, 2))

    @staticmethod
    def _paint_pin(painter, centre: QPointF) -> None:
        """A white map pin on an orange disc: the shape tells it, not only the colour."""
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(PIN_COLOUR)
        painter.drawEllipse(centre, 8, 8)
        painter.setBrush(QColor("white"))
        painter.drawEllipse(centre + QPointF(0, -2), 3.2, 3.2)
        painter.drawPolygon(QPolygonF([
            centre + QPointF(-2.6, 0), centre + QPointF(2.6, 0), centre + QPointF(0, 5.5),
        ]))


class MarkItem(QGraphicsItem):
    """A measurement. Passed is a disc, failed a triangle, not evaluated a hollow diamond."""

    def __init__(self, mark: TrackMark, label_height: int):
        super().__init__()
        self.mark = mark
        self.label_height = label_height
        self.show_label = False
        self.marked = False
        self.size = float(MARK_PX)
        if mark.verdict == Verdict.FAILED.value:
            self.setZValue(0.2)

    def set_size(self, size: float) -> None:
        if size != self.size:
            self.size = size
            self.update()

    def set_marked(self, marked: bool) -> None:
        if marked != self.marked:
            self.marked = marked
            self.update()

    def boundingRect(self) -> QRectF:
        return QRectF(-60, -self.label_height - MARK_PX, 120, self.label_height + 2 * MARK_PX)

    def shape(self) -> QPainterPath:
        return QPainterPath()

    def paint(self, painter, option, widget=None) -> None:
        palette = palette_of(self)
        if self.show_label:
            painter.setFont(small_font())
            painter.setPen(palette.color(QPalette.ColorRole.Text))
            top = -MARK_PX / 2 - self.label_height
            painter.drawText(QRectF(-60, top, 120, self.label_height),
                             Qt.AlignmentFlag.AlignCenter, self.mark.label)
        half = self.size / 2
        if self.marked:
            painter.setPen(QPen(palette.color(QPalette.ColorRole.Highlight), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(0, 0), half + 4, half + 4)
        colour = VERDICT_COLOURS.get(self.mark.verdict, VERDICT_COLOURS["not_evaluated"])
        if self.mark.verdict == Verdict.PASSED.value:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colour)
            painter.drawEllipse(QPointF(0, 0), half, half)
        elif self.mark.verdict == Verdict.FAILED.value:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(colour)
            painter.drawPolygon(QPolygonF([
                QPointF(0, -half - 1), QPointF(half + 1, half), QPointF(-half - 1, half),
            ]))
        else:
            painter.setPen(QPen(colour, 2))
            painter.setBrush(palette.color(QPalette.ColorRole.Base))
            painter.drawPolygon(QPolygonF([
                QPointF(0, -half), QPointF(half, 0), QPointF(0, half), QPointF(-half, 0),
            ]))
