# EasyMeasurement - easymeasurement/ui/verdict_marks.py
# A small mark per verdict, so a defect stands out in a long table at a glance.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap, QPolygonF

from ..model import Verdict

# Room for a fold arrow on the left and the mark on the right, the same in every row,
# so the text after it starts in one column.
MARK_SIZE = QSize(26, 14)
SCALE = 2  # drawn at twice the size, so it stays sharp on dense screens
_COLOURS = {Verdict.PASSED: "#27ae60", Verdict.FAILED: "#c0392b"}
_GREY = "#8a8f94"


def _arrow(painter: QPainter, opened: bool) -> None:
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(_GREY))
    points = ((1, 4), (9, 4), (5, 9.5)) if opened else ((3, 2.5), (8.5, 7), (3, 11.5))
    painter.drawPolygon(QPolygonF([QPointF(x, y) for x, y in points]))


@cache
def verdict_icon(verdict: str, opened: bool | None = None) -> QIcon:
    """A tick on green, a cross on red, an empty ring for what was not judged.

    Shape and colour both differ, so the marks also part for colour-blind eyes.
    `opened` adds the arrow of a line that folds several steps.
    """
    pixmap = QPixmap(MARK_SIZE * SCALE)
    pixmap.setDevicePixelRatio(SCALE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    if opened is not None:
        _arrow(painter, opened)
    painter.translate(12, 0)
    kind = Verdict(verdict)
    colour = QColor(_COLOURS.get(kind, _GREY))
    if kind not in _COLOURS:
        painter.setPen(QPen(colour, 1.6))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(7, 7), 5, 5)
        painter.end()
        return QIcon(pixmap)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(colour)
    painter.drawEllipse(QPointF(7, 7), 6.5, 6.5)
    pen = QPen(QColor("white"), 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    painter.setPen(pen)
    if kind == Verdict.PASSED:
        painter.drawPolyline([QPointF(4, 7.2), QPointF(6.2, 9.4), QPointF(10, 4.8)])
    else:
        painter.drawLine(QPointF(4.6, 4.6), QPointF(9.4, 9.4))
        painter.drawLine(QPointF(9.4, 4.6), QPointF(4.6, 9.4))
    painter.end()
    return QIcon(pixmap)
