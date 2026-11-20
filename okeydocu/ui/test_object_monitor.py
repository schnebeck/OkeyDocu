# OkeyDocu - okeydocu/ui/test_object_monitor.py
# Monitoring devices as test points: an insulation monitor and a residual current monitor.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A monitor switches nothing off: it raises an alarm, which the tester watches for. The
drawing shows the device with its alarm lamp, beside it the terminals of the conductors it
watches, where the probes go, and a PE bar. A residual current monitor watches through a
transformer around the conductors; the probes go on the load side of it."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..l10n import tr
from .test_object_parts import (
    BODY,
    CENTER,
    INK,
    LINE,
    Anchor,
    bold_font,
    pe_bar,
    screw,
    side_label,
)

PITCH = 40
FRAME, LAMP = QColor("#7d848b"), QColor("#f1c40f")


def _device(painter: QPainter, box: QRectF, sign: str, lines: list[str]) -> QRectF:
    """The monitor: its sign, what it states of itself and the alarm lamp."""
    device = QRectF(box.left() + box.width() * 0.08, box.top() + 56, 110, 110)
    painter.setPen(QPen(FRAME, 1.5))
    painter.setBrush(BODY)
    painter.drawRoundedRect(device, 6, 6)
    painter.setPen(INK)
    painter.setFont(bold_font(painter))
    painter.drawText(QRectF(device.left(), device.top() + 8, device.width(), 18), CENTER, sign)
    painter.setFont(QFont())
    for index, text in enumerate(lines[:2]):
        painter.drawText(QRectF(device.left(), device.top() + 30 + 16 * index, device.width(),
                                16), CENTER, text)
    lamp = QPointF(device.center().x(), device.bottom() - 24)
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(LAMP)
    painter.drawEllipse(lamp, 10, 10)
    painter.setPen(INK)
    painter.drawText(QRectF(device.left() - 30, device.bottom() + 4, device.width() + 60, 16),
                     CENTER, tr("Alarm lamp"))
    return device


def _terminals(painter: QPainter, box: QRectF, device: QRectF, names: list[str],
               side: str) -> tuple[QRectF, dict[str, QPointF]]:
    """The block of terminals the monitor watches, named by `side`; where each screw is."""
    block = QRectF(box.left() + box.width() * 0.33, box.top() + 70, 12 + PITCH * len(names), 96)
    painter.setPen(QPen(LINE, 1, Qt.PenStyle.DashLine))
    painter.drawLine(QPointF(device.right() + 8, device.center().y()),
                     QPointF(block.left() - 6, device.center().y()))
    painter.setPen(QPen(FRAME, 1.5))
    painter.setBrush(BODY)
    painter.drawRoundedRect(block, 6, 6)
    places = {}
    for index, name in enumerate(names):
        places[name] = QPointF(block.left() + 26 + index * PITCH, block.top() + 12)
        screw(painter, places[name], name, True)
        painter.setPen(QPen(LINE, 3))
        painter.drawLine(QPointF(places[name].x(), block.bottom()),
                         QPointF(places[name].x(), block.bottom() + 34))
    side_label(painter, block, True, side)
    return block, places


def imd(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
        n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    """An insulation monitor and the line conductors of its IT system: two, or three with
    `poles` above two."""
    device = _device(painter, box, "IMD", lines)
    names = ["L1", "L2", "L3"] if poles > 2 else ["L1", "L2"]
    block, places = _terminals(painter, box, device, names, tr("IT system"))
    pe = pe_bar(painter, QRectF(block.right() + 48, box.top() + 70, 150, 16))
    return {"l1": Anchor(places["L1"], -1), "l2": Anchor(places["L2"], -1), "pe": pe}


def rcm(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
        n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    """A residual current monitor, its transformer around the conductors below the terminals
    of the load side: L and N, or three line conductors and N with `poles` above two."""
    device = _device(painter, box, "RCM", lines)
    names = ["L1", "L2", "L3", "N"] if poles > 2 else ["L", "N"]
    block, places = _terminals(painter, box, device, names, tr("Load side"))
    ring = QRectF(block.left() + 8, block.bottom() + 10, block.width() - 16, 16)
    painter.setPen(QPen(INK, 2.5))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawEllipse(ring)
    painter.setPen(INK)
    painter.drawText(QRectF(block.left() - 96, ring.top() - 1, 90, 18),
                     Qt.AlignmentFlag.AlignRight, tr("Transformer"))
    pe = pe_bar(painter, QRectF(block.right() + 48, box.top() + 70, 150, 16))
    return {"out_l": Anchor(places[names[0]], -1), "out_n": Anchor(places["N"], -1), "pe": pe}
