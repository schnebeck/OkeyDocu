# OkeyDocu - okeydocu/ui/test_objects.py
# Drawings of the test point a guide sends the probes to, with the terminals they go on.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A drawing paints itself into a box and says where each terminal is and from which side a
probe reaches it: from below (+1) or from above (-1)."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..l10n import tr

INK, LINE = QColor("#1f2933"), QColor("#55595e")
BODY, SCREW = QColor("#f4f5f6"), QColor("#c9cdd1")
PE_BAR, PE_SCREW = QColor("#c8a43a"), QColor("#3aa845")
CENTER = Qt.AlignmentFlag.AlignCenter


@dataclass(frozen=True)
class Anchor:
    point: QPointF
    side: int  # +1: the probe comes from below, -1: from above


def _screw(painter: QPainter, centre: QPointF, label: str, above: bool) -> None:
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(SCREW)
    painter.drawEllipse(centre, 7, 7)
    painter.setPen(QPen(LINE, 1.5))
    painter.drawLine(QPointF(centre.x() - 4, centre.y()), QPointF(centre.x() + 4, centre.y()))
    painter.setPen(INK)
    offset = 8 if above else -22
    painter.drawText(QRectF(centre.x() - 10, centre.y() + offset, 20, 14), CENTER, label)


TERMINALS = {2: (("1", "2"), ("N", "N")),
             4: (("1", "2"), ("3", "4"), ("5", "6"), ("N", "N"))}
PITCH = 40  # between two poles


def rcd(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
        n_left: bool = False) -> dict[str, Anchor]:
    """An RCD with two or four poles, lever, test button and its data, and a PE bar beside it;
    supply terminals on top, outgoing ones below. N stands after the line conductors, or
    before them with `n_left`: N L1 L2 L3. Terminal numbers stand inside the housing, beside
    the screw they belong to."""
    terminals = TERMINALS[4 if poles > 2 else 2]
    if n_left:
        terminals = terminals[-1:] + terminals[:-1]
    width = 12 + PITCH * len(terminals)
    module = QRectF(box.left() + box.width() * 0.33, box.top() + 44, width, 150)
    bar = QRectF(module.right() + 48, box.top() + 70, 150, 16)
    painter.setPen(QPen(QColor("#7d848b"), 1.5))
    painter.setBrush(BODY)
    painter.drawRoundedRect(module, 6, 6)
    painter.setBrush(QColor("#2c3037"))
    painter.drawRoundedRect(QRectF(module.center().x() - 9, module.top() + 38, 18, 30), 3, 3)
    button = QPointF(module.right() - 16, module.top() + 46)
    painter.setBrush(QColor("#f1c40f"))
    painter.drawEllipse(button, 7, 7)
    painter.setPen(INK)
    painter.drawText(QRectF(button.x() - 7, button.y() - 7, 14, 14), CENTER, "T")
    bold = QFont(painter.font())
    bold.setBold(True)
    painter.setFont(bold)
    for index, text in enumerate(lines[:2]):
        painter.drawText(QRectF(module.left(), module.top() + 72 + 16 * index, module.width(),
                                16), CENTER, text)
    painter.setFont(QFont())
    for index, (top, low) in enumerate(terminals):
        x = module.left() + 26 + index * PITCH
        _screw(painter, QPointF(x, module.top() + 12), top, True)
        _screw(painter, QPointF(x, module.bottom() - 12), low, False)
    painter.drawText(QRectF(module.left() - 96, module.top() - 2, 90, 18),
                     Qt.AlignmentFlag.AlignRight, tr("Incoming"))
    painter.drawText(QRectF(module.left() - 96, module.bottom() - 20, 90, 18),
                     Qt.AlignmentFlag.AlignRight, tr("Outgoing"))
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(PE_BAR)
    painter.drawRoundedRect(bar, 3, 3)
    painter.setBrush(PE_SCREW)
    for index in range(6):
        painter.drawEllipse(QPointF(bar.left() + 14 + index * 24, bar.center().y()), 5, 5)
    painter.setPen(INK)
    painter.drawText(QRectF(bar.left(), bar.bottom() + 4, bar.width(), 16), CENTER,
                     tr("PE bar"))
    n_index = 0 if n_left else len(terminals) - 1
    l_index = 1 if n_left else 0
    l_x = module.left() + 26 + l_index * PITCH
    n_x = module.left() + 26 + n_index * PITCH
    return {"out_l": Anchor(QPointF(l_x, module.bottom() - 12), 1),
            "out_n": Anchor(QPointF(n_x, module.bottom() - 12), 1),
            "pe": Anchor(QPointF(bar.left() + 40, bar.top() + 4), -1)}


DRAWINGS = {"rcd": rcd}
