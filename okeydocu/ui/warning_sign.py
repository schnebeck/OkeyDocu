# OkeyDocu - okeydocu/ui/warning_sign.py
# The warning sign for electricity: a yellow triangle with a black edge and a black flash.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Drawn after the sign W012 of ISO 7010. All points are given in a square of 100 units, its
triangle standing on its base, and scaled into the box the caller names."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen

YELLOW, BLACK = QColor("#f9d000"), QColor("#111111")
TRIANGLE = ((50, 9), (95, 87), (5, 87))
EDGE = 7  # the black band, which also rounds the corners
FLASH = ((53, 36), (39, 59), (47, 57), (41, 70), (37, 69), (41, 80), (50, 73), (45, 71),
         (56, 51), (48, 53), (59, 36))


def _path(points, scale: float, origin: QPointF) -> QPainterPath:
    path = QPainterPath()
    for index, (x, y) in enumerate(points):
        point = QPointF(origin.x() + x * scale, origin.y() + y * scale)
        path.lineTo(point) if index else path.moveTo(point)
    path.closeSubpath()
    return path


def electricity_sign(painter: QPainter, box: QRectF) -> None:
    """As large as fits into `box`, centred in it."""
    side = min(box.width(), box.height())
    scale = side / 100
    origin = QPointF(box.center().x() - side / 2, box.center().y() - side / 2)
    painter.save()
    edge = QPen(BLACK, EDGE * scale)
    edge.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(edge)
    painter.setBrush(YELLOW)
    painter.drawPath(_path(TRIANGLE, scale, origin))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(BLACK)
    painter.drawPath(_path(FLASH, scale, origin))
    painter.restore()
