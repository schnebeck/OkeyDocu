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
from .test_object_climate import climate_sensor
from .test_object_current import supply_cores, touchable_part
from .test_object_monitor import imd, rcm
from .test_object_parts import (
    BODY,
    CENTER,
    INK,
    Anchor,
    bold_font,
    handle,
    pe_bar,
    screw,
    side_label,
)
from .test_object_plug import cee_plug
from .test_object_schuko import schuko_plug
from .test_object_switch import main_switch, main_switch_on, supply_pe

TERMINALS = {2: (("1", "2"), ("N", "N")),
             4: (("1", "2"), ("3", "4"), ("5", "6"), ("N", "N"))}
PITCH = 40  # between two poles


def rcd(painter: QPainter, box: QRectF, lines: list[str], poles: int = 2,
        n_left: bool = False, live: bool = True) -> dict[str, Anchor]:
    """An RCD with two or four poles, lever, test button and its data, the main switch's
    handle left of it and a PE bar right of it. The supply comes in at the lower terminals,
    the circuit leaves at the upper ones, where the probes go; the numbers stand as printed
    on the housing, beside the screw they belong to. N stands after the line conductors, or
    before them with `n_left`: N L1 L2 L3. Handle and lever are on while `live`."""
    terminals = TERMINALS[4 if poles > 2 else 2]
    if n_left:
        terminals = terminals[-1:] + terminals[:-1]
    handle(painter, QRectF(box.left() + box.width() * 0.08, box.top() + 56, 110, 110), live)
    width = 12 + PITCH * len(terminals)
    module = QRectF(box.left() + box.width() * 0.33, box.top() + 70, width, 150)
    painter.setPen(QPen(QColor("#7d848b"), 1.5))
    painter.setBrush(BODY)
    painter.drawRoundedRect(module, 6, 6)
    _lever(painter, module, live)
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
    side_label(painter, module, True, tr("Outgoing"))
    side_label(painter, module, False, tr("Incoming"))
    pe = pe_bar(painter, QRectF(module.right() + 48, box.top() + 70, 150, 16))
    n_index = 0 if n_left else len(terminals) - 1
    l_index = 1 if n_left else 0
    l_x = module.left() + 26 + l_index * PITCH
    n_x = module.left() + 26 + n_index * PITCH
    return {"out_l": Anchor(QPointF(l_x, module.top() + 12), -1),
            "out_n": Anchor(QPointF(n_x, module.top() + 12), -1),
            "pe": pe}


def _lever(painter: QPainter, module: QRectF, on: bool) -> None:
    """The lever in its slot: up when switched on, down when off."""
    slot = QRectF(module.center().x() - 10, module.top() + 32, 20, 38)
    painter.save()
    painter.setPen(QPen(QColor("#b3b9bf"), 1))
    painter.setBrush(QColor("#e1e4e7"))
    painter.drawRoundedRect(slot, 3, 3)
    painter.setPen(QPen(QColor("#7d848b"), 1.5))
    painter.setBrush(QColor("#2c3037"))
    painter.drawRoundedRect(QRectF(slot.left() + 1, slot.top() + (1 if on else 17), 18, 20), 3, 3)
    painter.restore()


DRAWINGS = {"rcd": rcd, "main_switch": main_switch, "cee_plug": cee_plug, "imd": imd,
            "rcm": rcm, "touchable_part": touchable_part, "supply_cores": supply_cores,
            "schuko_plug": schuko_plug, "main_switch_on": main_switch_on, "supply_pe": supply_pe,
            "climate_sensor": climate_sensor}
