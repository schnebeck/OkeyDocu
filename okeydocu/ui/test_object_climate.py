# OkeyDocu - okeydocu/ui/test_object_climate.py
# The place where a climate sensor is laid out: free air beside the equipment tested.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Drawn after no maker's picture: a cabinet as the equipment, beside it a small sensor with
its display, standing in free air, and the air moving past it. The sensor keeps a hand's width
from the cabinet, out of the warm air of its vents, out of sun and draught."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from ..l10n import tr
from .test_object_parts import INK, Anchor, bold_font

CABINET, SENSOR, SCREEN, AIR = QColor("#d7dbe0"), QColor("#f4f5f6"), QColor("#c9d6c3"), \
    QColor("#7fa6c9")


def _font(painter: QPainter, points: int) -> QFont:
    font = bold_font(painter)
    font.setPointSize(points)
    return font


def climate_sensor(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
                   n_left: bool = False, live: bool | None = None) -> dict[str, Anchor]:
    painter.save()
    painter.setPen(QPen(INK, 1.5))
    cabinet = QRectF(box.left() + box.width() * 0.08, box.top() + 20, box.width() * 0.3, 200)
    painter.setBrush(CABINET)
    painter.drawRect(cabinet)
    painter.setFont(_font(painter, 9))
    painter.drawText(cabinet.adjusted(0, 8, 0, 0), Qt.AlignmentFlag.AlignHCenter,
                     tr("Equipment"))
    sensor = QRectF(cabinet.right() + box.width() * 0.16, box.top() + 80, 76, 76)
    painter.setPen(QPen(AIR, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for offset in (-30, 0, 30):  # the air around it, drawn behind it
        start = QPointF(sensor.left() - 60, sensor.center().y() + offset)
        wave = QPainterPath(start)
        wave.cubicTo(start + QPointF(65, -14), start + QPointF(130, 14), start + QPointF(196, 0))
        painter.drawPath(wave)
    painter.setPen(QPen(INK, 1.5))
    painter.setBrush(SENSOR)
    painter.drawRoundedRect(sensor, 10, 10)
    screen = sensor.adjusted(10, 10, -10, -24)
    painter.setBrush(SCREEN)
    painter.drawRect(screen)
    painter.setFont(_font(painter, 10))
    painter.drawText(screen, Qt.AlignmentFlag.AlignCenter, "21.5\u00b0")
    painter.setFont(_font(painter, 7))
    painter.drawText(sensor.adjusted(0, 0, 0, -6), Qt.AlignmentFlag.AlignHCenter
                     | Qt.AlignmentFlag.AlignBottom, "38 %")
    painter.setPen(QPen(INK, 1.5))
    painter.setFont(_font(painter, 8))
    painter.drawText(QRectF(sensor.center().x() - 160, sensor.bottom() + 22, 320, 20),
                     Qt.AlignmentFlag.AlignHCenter, tr("free air, a hand's width away"))
    painter.restore()
    return {"sensor": Anchor(QPointF(sensor.center().x(), sensor.top()), -1)}
