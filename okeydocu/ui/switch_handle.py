# OkeyDocu - okeydocu/ui/switch_handle.py
# The handle of a main switch on its yellow plate, drawn switched off or switched on.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The knob turns a quarter: switched off its grip lies across, switched on it stands upright.
A window in the knob, opposite the grip, shows the position reached: “O OFF” at the left,
“I ON” at the top. Everything is drawn around the knob's centre with the grip to the right
and turned as a whole; only the words in the window stay upright."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

PLATE, PLATE_EDGE = QColor("#f5c81c"), QColor("#b8920a")
RED, RED_DARK, RED_LIGHT = QColor("#d3382d"), QColor("#a8271e"), QColor("#e9584c")
EDGE, STEEL, INK = QColor("#6e1811"), QColor("#c9cdd1"), QColor("#1f2933")
LOBES = 14  # the waves around the knob's rim
CENTER = Qt.AlignmentFlag.AlignCenter


def _rim(radius: float) -> QPainterPath:
    """A circle whose edge rises and falls a little, as a knob made to be gripped."""
    path = QPainterPath()
    steps = LOBES * 12
    for step in range(steps + 1):
        angle = 2 * math.pi * step / steps
        r = radius * (1 + 0.035 * math.cos(LOBES * angle))
        point = QPointF(r * math.cos(angle), r * math.sin(angle))
        path.lineTo(point) if step else path.moveTo(point)
    path.closeSubpath()
    return path


def _knob(painter: QPainter, radius: float, on: bool) -> None:
    """Rim, recess, window and grip, the grip pointing right. The light comes from the upper
    left of the picture, so its place on the knob follows the turn."""
    lit = QPointF(-radius * 0.4, radius * 0.3) if on else QPointF(-radius * 0.3, -radius * 0.4)
    shade = QRadialGradient(lit, radius * 1.6)
    shade.setColorAt(0, RED_LIGHT)
    shade.setColorAt(0.5, RED)
    shade.setColorAt(1, RED_DARK)
    painter.setPen(QPen(EDGE, 1.2))
    painter.setBrush(shade)
    painter.drawPath(_rim(radius))
    painter.setPen(QPen(RED_DARK, 1))
    painter.setBrush(RED.darker(108))
    painter.drawEllipse(QPointF(0, 0), radius * 0.76, radius * 0.76)
    painter.setPen(QPen(EDGE, 1))
    painter.setBrush(PLATE)
    painter.drawRoundedRect(_window(radius), 2, 2)
    grip = QRectF(-radius * 0.26, -radius * 0.2, radius * 1.42, radius * 0.4)
    bright, dim = (grip.bottomLeft(), grip.topLeft()) if on else \
        (grip.topLeft(), grip.bottomLeft())
    light = QLinearGradient(bright, dim)
    light.setColorAt(0, RED_LIGHT)
    light.setColorAt(1, RED_DARK)
    painter.setPen(QPen(EDGE, 1.2))
    painter.setBrush(light)
    painter.drawRoundedRect(grip, radius * 0.1, radius * 0.1)
    painter.setPen(QPen(INK, 0.8))
    painter.setBrush(STEEL)
    screw = QPointF(radius * 0.34, 0)
    painter.drawEllipse(screw, radius * 0.075, radius * 0.075)
    painter.drawLine(screw + QPointF(-radius * 0.05, 0), screw + QPointF(radius * 0.05, 0))


def _window(radius: float) -> QRectF:
    """Opposite the grip; it turns with the knob."""
    return QRectF(-radius * 0.72, -radius * 0.27, radius * 0.38, radius * 0.54)


def _position(painter: QPainter, centre: QPointF, radius: float, on: bool) -> None:
    """The words in the window, upright: at the left when off, at the top when on."""
    window = _window(radius)
    offset = abs(window.center().x())
    font = QFont(painter.font())
    font.setBold(True)
    font.setPointSizeF(max(radius * 0.13, 4.0))
    painter.setFont(font)
    painter.setPen(INK)
    if on:
        box = QRectF(centre.x() - window.height() / 2, centre.y() - offset - window.width() / 2,
                     window.height(), window.width())
        painter.drawText(box, CENTER, "I ON")
    else:
        box = QRectF(centre.x() - offset - window.width() / 2, centre.y() - window.height() / 2,
                     window.width(), window.height())
        painter.drawText(box, CENTER, "O\nOFF")


def switch_handle(painter: QPainter, plate: QRectF, on: bool) -> None:
    """The plate fills `plate`; the knob takes most of it. `on` turns the grip upright."""
    painter.save()
    painter.setPen(QPen(PLATE_EDGE, 1.5))
    painter.setBrush(PLATE)
    corner = plate.width() * 0.09
    painter.drawRoundedRect(plate, corner, corner)
    centre, radius = plate.center(), plate.width() * 0.4
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(0, 0, 0, 45))
    painter.drawEllipse(centre + QPointF(1.5, 2.5), radius * 1.04, radius * 1.04)
    painter.translate(centre)
    painter.rotate(90 if on else 0)
    _knob(painter, radius, on)
    painter.restore()
    painter.save()
    _position(painter, centre, radius, on)
    painter.restore()
