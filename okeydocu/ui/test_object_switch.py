# OkeyDocu - okeydocu/ui/test_object_switch.py
# The main switch as a test point: its handle, and the contact block behind it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The handle sits on the cabinet door; the probes go on the contact block behind it, which
the drawing shows beside the handle. The supply comes in at the upper terminals: L1, L2, L3
and N, or L and N for a single line conductor."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..l10n import tr
from .test_object_parts import BODY, CENTER, INK, LINE, Anchor, bold_font, handle, pe_bar, \
    screw, side_label

PITCH = 40
INCOMING = {"L": "in_l1", "L1": "in_l1", "L2": "in_l2", "L3": "in_l3", "N": "in_n"}


def main_switch(painter: QPainter, box: QRectF, lines: list[str], poles: int = 4,
                n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    """`poles` above two draw three line conductors and N, otherwise L and N; `n_left` puts
    N first; `live` draws the handle switched on."""
    incoming = ["L1", "L2", "L3", "N"] if poles > 2 else ["L", "N"]
    outgoing = ["2", "4", "6", "N"] if poles > 2 else ["2", "N"]
    if n_left:
        incoming, outgoing = incoming[-1:] + incoming[:-1], outgoing[-1:] + outgoing[:-1]
    plate = QRectF(box.left() + box.width() * 0.08, box.top() + 56, 110, 110)
    handle(painter, plate, live)
    module = QRectF(box.left() + box.width() * 0.33, box.top() + 70, 12 + PITCH * len(incoming),
                    160)
    painter.setPen(QPen(LINE, 1, Qt.PenStyle.DashLine))
    painter.drawLine(QPointF(plate.right() + 8, plate.center().y()),
                     QPointF(module.left() - 6, plate.center().y()))
    painter.setPen(QPen(QColor("#7d848b"), 1.5))
    painter.setBrush(BODY)
    painter.drawRoundedRect(module, 6, 6)
    painter.setBrush(QColor("#2c3037"))
    painter.drawEllipse(QPointF(module.center().x(), module.top() + 52), 12, 12)
    painter.setPen(INK)
    painter.setFont(bold_font(painter))
    for index, text in enumerate(lines[:2]):
        painter.drawText(QRectF(module.left(), module.top() + 74 + 16 * index,
                                module.width(), 16), CENTER, text)
    painter.setFont(QFont())
    anchors = {}
    for index, (top, low) in enumerate(zip(incoming, outgoing)):
        x = module.left() + 26 + index * PITCH
        screw(painter, QPointF(x, module.top() + 12), top, True)
        screw(painter, QPointF(x, module.bottom() - 12), low, False)
        anchors[INCOMING[top]] = Anchor(QPointF(x, module.top() + 12), -1)
    side_label(painter, module, True, tr("Incoming"))
    side_label(painter, module, False, tr("Outgoing"))
    anchors["pe"] = pe_bar(painter, QRectF(module.right() + 48, box.top() + 70, 150, 16))
    return anchors
