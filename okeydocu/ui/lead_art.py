# OkeyDocu - okeydocu/ui/lead_art.py
# A test lead as it is plugged in: plug over its socket row, grey lead, probe on its terminal.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The lead leaves the plug to the left, runs down a lane of its own beside the socket field
and reaches the probe from the side the terminal is approached from. Lanes are ordered like
the rows, the first row outermost, so that no two leads cross. `progress` from 0 to 1 draws
the lead as it is laid: the plug first, the lead growing towards the probe, the probe last.
Where the order of plugs and terminals forces two leads to cross, the later one bridges the
earlier one, with a light rim like a crossing in a cable plan."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen

from .test_objects import Anchor

LEAD, EDGE, PLUG = QColor("#8d949b"), QColor("#5f666d"), QColor("#b4bac0")
HALO = QColor(238, 241, 244, 230)  # a lead laid later runs visibly over one laid before
SHAFT, TIP, INK = QColor("#3a3f45"), QColor("#e9ebed"), QColor("#1f2933")
BEND = 14
PROBE = 64  # from tip to the end of the handle
SAMPLES = 80


def route(start: QPointF, lane: float, anchor: Anchor, depth: float) -> QPainterPath:
    """From the plug to the end of the probe's handle; `depth` keeps leads that approach
    from the same side apart where they turn."""
    grip = QPointF(anchor.point.x(), anchor.point.y() + anchor.side * PROBE)
    turn = grip.y() + anchor.side * depth
    path = QPainterPath(start)
    path.lineTo(lane + BEND, start.y())
    path.quadTo(lane, start.y(), lane, start.y() + BEND)
    path.lineTo(lane, turn - BEND)
    path.quadTo(lane, turn, lane + BEND, turn)
    path.lineTo(grip.x() - BEND, turn)
    path.quadTo(grip.x(), turn, grip.x(), turn - anchor.side * BEND)
    path.lineTo(grip)
    return path


def partial(path: QPainterPath, fraction: float) -> QPainterPath:
    """The first `fraction` of a path, as laid out so far."""
    if fraction >= 1:
        return path
    cut = QPainterPath(path.pointAtPercent(0))
    for step in range(1, int(SAMPLES * fraction) + 1):
        cut.lineTo(path.pointAtPercent(path.percentAtLength(path.length() * step / SAMPLES)))
    return cut


def paint_plug(painter: QPainter, plug: QRectF, marking: str) -> None:
    painter.setPen(QPen(EDGE, 1.5))
    painter.setBrush(PLUG)
    painter.drawRoundedRect(plug, 7, 7)
    bold = QFont(painter.font())
    bold.setBold(True)
    painter.setFont(bold)
    painter.setPen(INK)
    painter.drawText(plug, Qt.AlignmentFlag.AlignCenter, marking)


def paint_probe(painter: QPainter, anchor: Anchor, marking: str, left: bool) -> None:
    tip, side = anchor.point, anchor.side
    guard = QPointF(tip.x(), tip.y() + side * 18)
    grip_y = tip.y() + side * PROBE
    handle = QRectF(tip.x() - 7, min(guard.y(), grip_y), 14, abs(grip_y - guard.y()))
    painter.setPen(QPen(EDGE, 1.2))
    painter.setBrush(PLUG)
    painter.drawRoundedRect(handle, 5, 5)
    painter.drawEllipse(guard, 11, 4)
    painter.setPen(QPen(SHAFT, 3))
    painter.drawLine(guard, tip)
    painter.setPen(QPen(TIP, 2))
    painter.drawLine(QPointF(tip.x(), tip.y() + side * 6), tip)
    painter.setPen(INK)
    if left:
        where, align = QRectF(handle.left() - 96, handle.center().y() - 10, 90, 20), \
            Qt.AlignmentFlag.AlignRight
    else:
        where, align = QRectF(handle.right() + 6, handle.center().y() - 10, 90, 20), \
            Qt.AlignmentFlag.AlignLeft
    painter.drawText(where, align | Qt.AlignmentFlag.AlignVCenter, marking)


def paint_lead(painter: QPainter, plug: QRectF, marking: str, path: QPainterPath,
               anchor: Anchor, probe: str, left: bool, progress: float) -> None:
    if progress <= 0:
        return
    laid = partial(path, min(progress / 0.85, 1.0))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for color, width in ((HALO, 12), (LEAD, 6)):
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(laid)
    paint_plug(painter, plug, marking)
    if progress >= 0.85:
        paint_probe(painter, anchor, probe, left)
