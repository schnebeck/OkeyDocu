# OkeyDocu - okeydocu/ui/test_object_schuko.py
# The Schuko plug of a machine as a test point, with the machine housing it belongs to.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The plug is seen from its contact side: a round black face with two pins side by side and
the earthing clips as brass strips at its upper and lower edge. A Schuko plug fits either way
round, so its pins carry no fixed L and N. Beside it a bare metal spot on the housing."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..l10n import tr
from .test_object_parts import CENTER, INK, LINE, Anchor, bold_font, metal_part

FACE_COLOUR, RIM = QColor("#2c3037"), QColor("#4a5058")
BRASS = QColor("#d9b84a")
FACE = 64  # radius of the plug face
PIN_OFFSET = 32  # half the distance between the pins
CLIP = QRectF(-14, -6, 28, 12)  # an earthing clip around its centre, clear of the pins


def _clip(painter: QPainter, centre: QPointF) -> None:
    painter.setPen(QPen(LINE, 1))
    painter.setBrush(BRASS)
    painter.drawRoundedRect(CLIP.translated(centre), 4, 4)


def schuko_plug(painter: QPainter, box: QRectF, lines: list[str], poles: int = 4,
                n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    centre = QPointF(box.left() + box.width() * 0.40, box.top() + 44 + FACE + 10)
    painter.setPen(QPen(LINE, 1.5))
    painter.setBrush(RIM)
    painter.drawEllipse(centre, FACE + 10, FACE + 10)
    painter.setBrush(FACE_COLOUR)
    painter.drawEllipse(centre, FACE - 4, FACE - 4)
    top = QPointF(centre.x(), centre.y() - FACE - 2)
    bottom = QPointF(centre.x(), centre.y() + FACE + 2)
    _clip(painter, top)
    _clip(painter, bottom)
    anchors = {"pe_pin": Anchor(QPointF(bottom.x(), bottom.y() + 6), 1)}
    for name, side in (("1", -1), ("2", 1)):
        pin = QPointF(centre.x() + side * PIN_OFFSET, centre.y())
        painter.setPen(QPen(LINE, 1))
        painter.setBrush(BRASS)
        painter.drawEllipse(pin, 8, 8)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(pin.x() - 12, pin.y() + 12, 24, 16), CENTER, name)
        key = "l_pin" if side < 0 else "n_pin"
        anchors[key] = Anchor(QPointF(pin.x(), pin.y() - 6), -1, side < 0)
    painter.setPen(INK)
    painter.setFont(bold_font(painter))
    caption = " · ".join([tr("Schuko plug, contact side"), *lines[:1]])
    beside = QRectF(box.left() + box.width() * 0.72, box.top() + 58, box.width() * 0.26, 36)
    painter.drawText(beside, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap, caption)
    painter.setFont(QFont())
    note = QRectF(box.left() + box.width() * 0.72, box.top() + 100, box.width() * 0.26, 54)
    painter.drawText(note, Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                     tr("It fits either way round: pins 1 and 2 have no fixed L and N."))
    housing = QRectF(box.left() + box.width() * 0.56, box.top() + 40, box.width() * 0.14, 150)
    anchors["body"] = metal_part(painter, housing, tr("Machine housing"), tr("bare metal"))
    return anchors
