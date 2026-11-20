# OkeyDocu - okeydocu/ui/test_object_current.py
# Test points of the current measurements: a touchable part, and the cores a clamp closes around.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Both are measured on the running machine, so the main switch's handle stands switched on
beside them. The touch current flows from a conductive part that is not on the protective
conductor to the PE bar. The clamp closes around the protective conductor alone, which leaves
the supply cable apart from the line conductors and N."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen

from ..l10n import tr
from .test_object_parts import INK, LINE, Anchor, handle, metal_part, pe_bar

CORES = {"L": "#8b5a2b", "L1": "#8b5a2b", "L2": "#22262b", "L3": "#8d949b", "N": "#2f6fbf"}
GREEN, YELLOW, SHEATH = QColor("#3aa845"), QColor("#f1c40f"), QColor("#3a3f45")
PITCH = 13  # between two cores


def _handle(painter: QPainter, box: QRectF, live: bool) -> None:
    handle(painter, QRectF(box.left() + box.width() * 0.08, box.top() + 56, 110, 110), live)


def touchable_part(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
                   n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    """A conductive part of the machine with a bare spot, and the PE bar the current is
    measured against."""
    _handle(painter, box, live)
    part = QRectF(box.left() + box.width() * 0.33, box.top() + 40, box.width() * 0.15, 150)
    spot = metal_part(painter, part, tr("Touchable part"), tr("not on PE"))
    return {"part": spot,
            "pe": pe_bar(painter, QRectF(part.right() + 80, box.top() + 70, 150, 16))}


def supply_cores(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
                 n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    """The cores of the supply cable spread out of its sheath: the line conductors and N
    together, the protective conductor apart, where the clamp closes around it."""
    _handle(painter, box, live)
    names = ["L1", "L2", "L3", "N"] if poles > 2 else ["L", "N"]
    left, right = box.left() + box.width() * 0.36, box.left() + box.width() * 0.66
    top = box.top() + 60
    earth = top + PITCH * len(names) + 36
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(SHEATH)
    painter.drawRoundedRect(QRectF(left - 46, top - 10, 46, earth - top + 20), 6, 6)
    for index, name in enumerate(names):
        y = top + index * PITCH
        painter.setPen(QPen(QColor(CORES[name]), 6, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawLine(QPointF(left, y), QPointF(right, y))
        painter.setPen(INK)
        painter.drawText(QRectF(right + 8, y - 8, 30, 16), Qt.AlignmentFlag.AlignVCenter, name)
    painter.setPen(QPen(GREEN, 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(QPointF(left, earth), QPointF(right, earth))
    painter.setPen(QPen(YELLOW, 3, Qt.PenStyle.DashLine, Qt.PenCapStyle.FlatCap))
    painter.drawLine(QPointF(left + 4, earth), QPointF(right - 4, earth))
    painter.setPen(INK)
    painter.drawText(QRectF(right + 8, earth - 8, 160, 16), Qt.AlignmentFlag.AlignVCenter,
                     tr("PE: protective conductor"))
    return {"pe_core": Anchor(QPointF((left + right) / 2, earth), 1)}
