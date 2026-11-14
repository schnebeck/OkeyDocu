# OkeyDocu - okeydocu/ui/place_scene.py
# Station "Installation": the element measured at, its test point, and how to prepare it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The element's path and name on top, its test point drawn as the leads station shows it,
the state the installation stays in below, beside it what to do beforehand."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..campaign.measuring_place import MeasuringPlace
from ..devices.guide import Guide
from ..l10n import tr
from .test_objects import DRAWINGS

INK, MUTED, FRAME = QColor("#1f2933"), QColor("#5f666d"), QColor("#9aa5ae")
LIVE, LIVE_BACK, LIVE_INK = QColor("#e67e22"), QColor("#fff4e5"), QColor("#b35c00")
DEAD, DEAD_BACK, DEAD_INK = QColor("#2e8b57"), QColor("#e8f5ee"), QColor("#1e6b41")
SCALE = 1.3  # the test point drawn a little larger than on the bench
BOLT = ((18, 0), (3, 34), (21, 34), (-12, 88), (-5, 50), (-23, 50))


def _font(size: int, bold: bool = False) -> QFont:
    font = QFont()
    font.setPointSize(size)
    font.setBold(bold)
    return font


class PlaceScene(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.guide: Guide | None = None
        self.place = MeasuringPlace(None)
        self.setMinimumSize(640, 520)

    def show_place(self, guide: Guide, place: MeasuringPlace) -> None:
        self.guide, self.place = guide, place
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        box = QRectF(20, 20, self.width() - 40, self.height() - 40)
        painter.setPen(QPen(FRAME, 1.5))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(box, 10, 10)
        if self.guide is None:
            return
        self._paint_title(painter, box)
        if self.place.asset_id is not None or self.place.kind:
            painter.save()
            painter.translate(box.left() + 10, box.top() + 90)
            painter.scale(SCALE, SCALE)
            painter.setFont(_font(8))
            lines = self.place.lines(self.guide.drawing_features)
            DRAWINGS[self.guide.test_object](
                painter, QRectF(0, 0, (box.width() - 20) / SCALE, 230), lines,
                self.place.poles, self.place.n_left)
            painter.restore()
        state = QRectF(box.left() + 24, box.top() + 400, box.width() * 0.42, 220)
        self._paint_state(painter, state)
        self._paint_preparation(painter, QRectF(state.right() + 24, state.top(),
                                                box.right() - state.right() - 48, 220))

    def _paint_title(self, painter: QPainter, box: QRectF) -> None:
        painter.setFont(_font(11))
        painter.setPen(MUTED)
        trail = "  ›  ".join(self.place.path)
        painter.drawText(box.adjusted(24, 18, -24, 0), trail + ("  ›" if trail else ""))
        painter.setFont(_font(15, True))
        painter.setPen(INK)
        title = self.place.title or tr("No element chosen yet")
        painter.drawText(box.adjusted(24, 44, -24, 0), title)

    def _paint_state(self, painter: QPainter, state: QRectF) -> None:
        live = self.guide.live
        line, back, ink = (LIVE, LIVE_BACK, LIVE_INK) if live else (DEAD, DEAD_BACK, DEAD_INK)
        painter.setPen(QPen(line, 2))
        painter.setBrush(back)
        painter.drawRoundedRect(state, 14, 14)
        if live:
            x, y = state.left() + 44, state.top() + 52
            bolt = QPainterPath(QPointF(x + BOLT[0][0], y + BOLT[0][1]))
            for dx, dy in BOLT[1:]:
                bolt.lineTo(QPointF(x + dx, y + dy))
            bolt.closeSubpath()
            painter.setPen(QPen(INK, 1.5))
            painter.setBrush(QColor("#f1c40f"))
            painter.drawPath(bolt)
        heading = tr("Live") if live else tr("De-energised")
        text = (tr("The circuit stays switched on.") if live else
                tr("Switch off, secure against switching on again, verify that it is dead."))
        painter.setFont(_font(16, True))
        painter.setPen(ink)
        painter.drawText(QRectF(state.left() + 100, state.top() + 40, state.width() - 110, 34),
                         heading)
        painter.setFont(_font(11))
        painter.setPen(INK)
        painter.drawText(QRectF(state.left() + 100, state.top() + 84, state.width() - 116, 110),
                         Qt.TextFlag.TextWordWrap, text)

    def _paint_preparation(self, painter: QPainter, area: QRectF) -> None:
        for index, (heading, text) in enumerate(self.guide.preparation):
            tile = QRectF(area.left(), area.top() + index * 76, area.width(), 66)
            painter.setPen(QPen(FRAME, 1.2))
            painter.setBrush(QColor("#f7f8f9"))
            painter.drawRoundedRect(tile, 10, 10)
            painter.setFont(_font(11, True))
            painter.setPen(INK)
            painter.drawText(QRectF(tile.left() + 16, tile.top() + 10, tile.width() - 24, 20),
                             tr(heading))
            painter.setFont(_font(10))
            painter.setPen(MUTED)
            painter.drawText(QRectF(tile.left() + 16, tile.top() + 32, tile.width() - 24, 30),
                             Qt.TextFlag.TextWordWrap, tr(text))
