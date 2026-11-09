# EasyMeasurement - easymeasurement/ui/verdict_marks.py
# A small mark per verdict, so a defect stands out in a long table at a glance.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from functools import cache

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from ..model import Verdict

SIZE, SCALE = 14, 2  # drawn at twice the size, so it stays sharp on dense screens
_COLOURS = {Verdict.PASSED: "#27ae60", Verdict.FAILED: "#c0392b"}


@cache
def verdict_icon(verdict: str) -> QIcon:
    """A tick on green, a cross on red, an empty ring for what was not judged.

    Shape and colour both differ, so the marks also part for colour-blind eyes.
    """
    pixmap = QPixmap(SIZE * SCALE, SIZE * SCALE)
    pixmap.setDevicePixelRatio(SCALE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    kind = Verdict(verdict)
    colour = QColor(_COLOURS.get(kind, "#8a8f94"))
    if kind not in _COLOURS:
        painter.setPen(QPen(colour, 1.6))
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
