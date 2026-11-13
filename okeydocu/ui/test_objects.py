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

from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPen

from ..l10n import tr
from .test_object_parts import BODY, CENTER, INK, Anchor, bold_font, pe_bar, screw, side_label
from .test_object_plug import cee_plug
from .test_object_switch import main_switch

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
    painter.setFont(bold_font(painter))
    for index, text in enumerate(lines[:2]):
        painter.drawText(QRectF(module.left(), module.top() + 72 + 16 * index, module.width(),
                                16), CENTER, text)
    painter.setFont(QFont())
    for index, (top, low) in enumerate(terminals):
        x = module.left() + 26 + index * PITCH
        screw(painter, QPointF(x, module.top() + 12), top, True)
        screw(painter, QPointF(x, module.bottom() - 12), low, False)
    side_label(painter, module, True, tr("Incoming"))
    side_label(painter, module, False, tr("Outgoing"))
    pe = pe_bar(painter, bar)
    n_index = 0 if n_left else len(terminals) - 1
    l_index = 1 if n_left else 0
    l_x = module.left() + 26 + l_index * PITCH
    n_x = module.left() + 26 + n_index * PITCH
    return {"out_l": Anchor(QPointF(l_x, module.bottom() - 12), 1),
            "out_n": Anchor(QPointF(n_x, module.bottom() - 12), 1),
            "pe": pe}


DRAWINGS = {"rcd": rcd, "main_switch": main_switch, "cee_plug": cee_plug}
