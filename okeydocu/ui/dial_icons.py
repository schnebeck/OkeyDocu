# OkeyDocu - okeydocu/ui/dial_icons.py
# The marking of a dial position as printed on the instrument, as a small badge.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The badge is cut from the drawing of the front panel: the part `pos-<value>` on the panel's
own dark colour, so the list of measurements shows what the tester finds on the dial. Every
badge has the same size and the marking is centred in it, so the names beside them line up.
An instrument without a drawing, or a position without a marking, gives no badge."""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

BADGE = QSize(46, 20)  # logical pixels
PANEL = QColor("#2c3037")
INSET = 3  # between the badge's edge and the marking
SCALE = 2  # pixels per logical pixel, sharp on fine screens too


@lru_cache(maxsize=4)
def _renderer(path: str) -> QSvgRenderer:
    return QSvgRenderer(path)


def dial_icon(drawing, value: int | None) -> QIcon:
    if drawing is None or value is None:
        return QIcon()
    renderer = _renderer(str(drawing.front))
    element = f"pos-{value}"
    if not renderer.elementExists(element):
        return QIcon()
    bounds = renderer.boundsOnElement(element)
    pixmap = QPixmap(BADGE * SCALE)
    pixmap.setDevicePixelRatio(SCALE)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(PANEL)
    painter.drawRoundedRect(QRectF(0, 0, BADGE.width(), BADGE.height()), 4, 4)
    room = QRectF(INSET, INSET, BADGE.width() - 2 * INSET, BADGE.height() - 2 * INSET)
    scale = min(room.width() / bounds.width(), room.height() / bounds.height())
    width, height = bounds.width() * scale, bounds.height() * scale
    renderer.render(painter, element, QRectF(room.center().x() - width / 2,
                                             room.center().y() - height / 2, width, height))
    painter.end()
    return QIcon(pixmap)
