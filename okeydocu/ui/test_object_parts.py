# OkeyDocu - okeydocu/ui/test_object_parts.py
# What the drawings of test points share: anchors for the probes, screws, the PE bar.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

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


def screw(painter: QPainter, centre: QPointF, label: str, above: bool) -> None:
    """A terminal screw, its label on the side away from where the probe comes."""
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(SCREW)
    painter.drawEllipse(centre, 7, 7)
    painter.setPen(QPen(LINE, 1.5))
    painter.drawLine(QPointF(centre.x() - 4, centre.y()), QPointF(centre.x() + 4, centre.y()))
    painter.setPen(INK)
    offset = 8 if above else -22
    painter.drawText(QRectF(centre.x() - 10, centre.y() + offset, 20, 14), CENTER, label)


def pe_bar(painter: QPainter, bar: QRectF) -> Anchor:
    """A PE bar with its green screws; the probe comes from above, near its left end."""
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(PE_BAR)
    painter.drawRoundedRect(bar, 3, 3)
    painter.setBrush(PE_SCREW)
    for index in range(int((bar.width() - 4) // 24)):
        painter.drawEllipse(QPointF(bar.left() + 14 + index * 24, bar.center().y()), 5, 5)
    painter.setPen(INK)
    painter.drawText(QRectF(bar.left(), bar.bottom() + 4, bar.width(), 16), CENTER,
                     tr("PE bar"))
    return Anchor(QPointF(bar.left() + 40, bar.top() + 4), -1)


def side_label(painter: QPainter, module: QRectF, top: bool, text: str) -> None:
    """A word left of a module, level with its upper or lower row of terminals."""
    y = module.top() - 2 if top else module.bottom() - 20
    painter.setPen(INK)
    painter.drawText(QRectF(module.left() - 96, y, 90, 18), Qt.AlignmentFlag.AlignRight, text)


def bold_font(painter: QPainter) -> QFont:
    bold = QFont(painter.font())
    bold.setBold(True)
    return bold
