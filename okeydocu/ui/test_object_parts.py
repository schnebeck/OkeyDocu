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
from .switch_handle import switch_handle

INK, LINE = QColor("#1f2933"), QColor("#55595e")
BODY, SCREW = QColor("#f4f5f6"), QColor("#c9cdd1")
PE_BAR, PE_SCREW, PE_RECESS = QColor("#c8a43a"), QColor("#3aa845"), QColor("#1d6b27")
CENTER = Qt.AlignmentFlag.AlignCenter
TILT = 0.36  # how far a cross recess is turned out of the upright, as a share of its reach


@dataclass(frozen=True)
class Anchor:
    point: QPointF
    side: int  # +1: the probe comes from below, -1: from above
    mark_left: bool = False  # the probe's marking stands left of it: the right is taken


def cross(painter: QPainter, centre: QPointF, reach: float) -> None:
    """The cross recess of a screw head, turned a little as a tightened screw comes to rest."""
    for along, across in ((reach, reach * TILT), (-reach * TILT, reach)):
        arm = QPointF(along, across)
        painter.drawLine(centre - arm, centre + arm)


def screw(painter: QPainter, centre: QPointF, label: str, above: bool) -> None:
    """A terminal screw, its label on the side away from where the probe comes."""
    painter.setPen(QPen(LINE, 1.2))
    painter.setBrush(SCREW)
    painter.drawEllipse(centre, 7, 7)
    painter.setPen(QPen(LINE, 1.4))
    cross(painter, centre, 4.2)
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
        head = QPointF(bar.left() + 14 + index * 24, bar.center().y())
        painter.setPen(QPen(LINE, 1.2))
        painter.drawEllipse(head, 5, 5)
        painter.setPen(QPen(PE_RECESS, 1.1))
        cross(painter, head, 2.8)
    painter.setPen(INK)
    painter.drawText(QRectF(bar.left(), bar.bottom() + 4, bar.width(), 16), CENTER,
                     tr("PE bar"))
    return Anchor(QPointF(bar.left() + 40, bar.top() + 4), -1)


def side_label(painter: QPainter, module: QRectF, top: bool, text: str) -> None:
    """A word left of a module, level with its upper or lower row of terminals."""
    y = module.top() - 2 if top else module.bottom() - 20
    painter.setPen(INK)
    painter.drawText(QRectF(module.left() - 96, y, 90, 18), Qt.AlignmentFlag.AlignRight, text)


def handle(painter: QPainter, plate: QRectF, on: bool) -> None:
    """The main switch's handle with the position it is in written below."""
    switch_handle(painter, plate, on)
    painter.setPen(INK)
    caption = tr("Main switch: on") if on else tr("Main switch: off")
    painter.drawText(QRectF(plate.left() - 30, plate.bottom() + 4, plate.width() + 60, 16),
                     CENTER, caption)


def bold_font(painter: QPainter) -> QFont:
    bold = QFont(painter.font())
    bold.setBold(True)
    return bold
