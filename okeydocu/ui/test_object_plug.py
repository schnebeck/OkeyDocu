# OkeyDocu - okeydocu/ui/test_object_plug.py
# The CEE plug of a machine as a test point, with the machine housing it belongs to.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The plug is seen from its contact side: a red five-pole plug for three line conductors,
a blue three-pole one for a single line conductor, the earth contact in the clock position
6 h, larger than the others. Beside it a bare metal spot on the housing, where the second
probe goes."""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..l10n import tr
from .test_object_parts import CENTER, INK, LINE, Anchor, bold_font

RED, BLUE = QColor("#d64534"), QColor("#2f6fbf")
PIN, HOUSING, BARE = QColor("#d9b84a"), QColor("#b9c0c7"), QColor("#e8eaec")
FACE = 64  # radius of the plug face


def _pins(poles: int) -> list[tuple[str, float]]:
    """Name and clock angle in degrees from the top of each contact."""
    if poles > 2:
        return [("L1", 300.0), ("L2", 0.0), ("L3", 60.0), ("N", 120.0), ("PE", 180.0)]
    return [("L", 60.0), ("N", 300.0), ("PE", 180.0)]


def cee_plug(painter: QPainter, box: QRectF, lines: list[str], poles: int = 4,
             n_left: bool = False) -> dict[str, Anchor]:
    centre = QPointF(box.left() + box.width() * 0.40, box.top() + 44 + FACE + 10)
    painter.setPen(QPen(LINE, 1.5))
    painter.setBrush(RED if poles > 2 else BLUE)
    painter.drawEllipse(centre, FACE + 10, FACE + 10)
    painter.setBrush(QColor("#2c3037"))
    painter.drawEllipse(centre, FACE - 4, FACE - 4)
    anchors = {}
    for name, angle in _pins(poles):
        radius = 38
        point = QPointF(centre.x() + radius * math.sin(math.radians(angle)),
                        centre.y() - radius * math.cos(math.radians(angle)))
        size = 10 if name == "PE" else 7
        painter.setPen(QPen(LINE, 1))
        painter.setBrush(PIN)
        painter.drawEllipse(point, size, size)
        painter.setPen(QColor("#ffffff"))
        label = QPointF(centre.x() + 58 * math.sin(math.radians(angle)) - 12,
                        centre.y() - 54 * math.cos(math.radians(angle)) - 8)
        if name == "PE":  # its probe comes from below, the label stands beside the contact
            label = QPointF(point.x() - 40, point.y() - 8)
        painter.drawText(QRectF(label, label + QPointF(24, 16)), CENTER, name)
        if name == "PE":
            anchors["pe_pin"] = Anchor(QPointF(point.x(), point.y() + size - 2), 1)
    painter.setPen(INK)
    painter.setFont(bold_font(painter))
    caption = " · ".join([tr("CEE plug, contact side"), *lines[:1]])
    painter.drawText(QRectF(centre.x() - 140, box.top() + 12, 280, 16), CENTER, caption)
    painter.setFont(QFont())
    housing = QRectF(box.left() + box.width() * 0.56, box.top() + 40, box.width() * 0.14, 150)
    painter.setPen(QPen(LINE, 1.5))
    painter.setBrush(HOUSING)
    painter.drawRoundedRect(housing, 8, 8)
    spot = QPointF(housing.center().x(), housing.bottom() - 30)
    painter.setBrush(BARE)
    painter.drawEllipse(spot, 14, 10)
    painter.setPen(INK)
    painter.drawText(QRectF(housing.left(), housing.top() + 10, housing.width(), 18), CENTER,
                     tr("Machine housing"))
    painter.drawText(QRectF(housing.left(), spot.y() - 36, housing.width(), 18), CENTER,
                     tr("bare metal"))
    anchors["body"] = Anchor(QPointF(spot.x(), spot.y() + 8), 1)
    return anchors
