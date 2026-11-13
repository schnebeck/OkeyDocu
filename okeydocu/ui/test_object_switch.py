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
from .test_object_parts import BODY, CENTER, INK, LINE, Anchor, bold_font, pe_bar, screw, \
    side_label

PITCH = 40
PLATE, HANDLE = QColor("#f2c418"), QColor("#c0392b")


def _handle(painter: QPainter, plate: QRectF) -> None:
    painter.setPen(QPen(LINE, 1.5))
    painter.setBrush(PLATE)
    painter.drawRoundedRect(plate, 6, 6)
    centre = plate.center()
    painter.setBrush(HANDLE)
    painter.drawEllipse(centre, 22, 22)
    painter.save()
    painter.translate(centre)
    painter.rotate(-45)
    painter.drawRoundedRect(QRectF(-9, -38, 18, 76), 6, 6)
    painter.restore()
    painter.setPen(INK)
    painter.drawText(QRectF(plate.left(), plate.top() + 4, plate.width(), 14), CENTER, "0")
    painter.drawText(QRectF(plate.right() - 20, plate.top() + 4, 16, 14), CENTER, "I")
    painter.drawText(QRectF(plate.left() - 20, plate.bottom() + 4, plate.width() + 40, 16),
                     CENTER, tr("Main switch"))


def main_switch(painter: QPainter, box: QRectF, lines: list[str], poles: int = 4,
                n_left: bool = False) -> dict[str, Anchor]:
    """`poles` above two draw three line conductors and N, otherwise L and N; `n_left` puts
    N first."""
    incoming = ["L1", "L2", "L3", "N"] if poles > 2 else ["L", "N"]
    outgoing = ["2", "4", "6", "N"] if poles > 2 else ["2", "N"]
    if n_left:
        incoming, outgoing = incoming[-1:] + incoming[:-1], outgoing[-1:] + outgoing[:-1]
    plate = QRectF(box.left() + box.width() * 0.08, box.top() + 56, 110, 110)
    _handle(painter, plate)
    module = QRectF(box.left() + box.width() * 0.33, box.top() + 70, 12 + PITCH * len(incoming),
                    160)
    painter.setPen(QPen(LINE, 1, Qt.PenStyle.DashLine))
    painter.drawLine(QPointF(plate.right() + 8, plate.center().y()),
                     QPointF(module.left() - 100, plate.center().y()))
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
        key = "in_n" if top == "N" else "in_l1" if top in ("L1", "L") else ""
        if key:
            anchors[key] = Anchor(QPointF(x, module.top() + 12), -1)
    side_label(painter, module, True, tr("Incoming"))
    side_label(painter, module, False, tr("Outgoing"))
    anchors["pe"] = pe_bar(painter, QRectF(module.right() + 48, box.top() + 70, 150, 16))
    return anchors
