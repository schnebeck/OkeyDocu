# OkeyDocu - okeydocu/ui/pixel_lines.py
# Frames and rules laid on the screen's own pixels, whatever the window is scaled by.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A window scaled by a fraction puts the edges of a widget between two pixels. Qt rounds
the area a widget may paint to whole pixels; a line drawn in the widget's own units is
rounded on its own, so it can fall on the pixel just outside and vanish, or come out twice
as thick as its neighbour. Here the area is rounded first, the way Qt rounds it, and each
line is laid along an edge of that area. Widgets that touch share the rounded edge, so
their lines meet."""

from __future__ import annotations

import math

from PySide6.QtCore import QRect, QRectF
from PySide6.QtGui import QColor, QPainter

LINE = 1  # room a line takes in a layout


def _whole(value: float) -> int:
    return math.floor(value + 0.5)


def line_width(painter: QPainter) -> int:
    """Pixels a line is thick: never more than the room a layout keeps for it."""
    return max(1, math.floor(painter.device().devicePixelRatioF()))


def device_rect(painter: QPainter, rect: QRect) -> QRect:
    """The pixels `rect` covers, given in the painter's own units."""
    area = painter.deviceTransform().mapRect(QRectF(rect))
    left, top = _whole(area.left()), _whole(area.top())
    return QRect(left, top, _whole(area.right()) - left, _whole(area.bottom()) - top)


def fill(painter: QPainter, pixels: QRect, colour: QColor) -> None:
    back, _ = painter.deviceTransform().inverted()
    painter.fillRect(back.mapRect(QRectF(pixels)), colour)


def frame(painter: QPainter, rect: QRect, colour: QColor, top: bool = True,
          joined: bool = False) -> None:
    """A closed line around what stands in `rect`, one LINE in from its edges. It lies on
    the pixels next to the inside, so whatever fills the inside reaches the line.

    Blocks standing on each other share one frame: without `top` the sides begin at the
    first pixel, where the block above ends; `joined`, the line below lies on the last
    pixels, where the block below begins."""
    thick = line_width(painter)
    outer = device_rect(painter, rect)
    inner = device_rect(painter, rect.adjusted(LINE, LINE if top else 0, -LINE, -LINE))
    left, right = inner.left() - thick, inner.right() + 1
    width = inner.width() + 2 * thick
    first = inner.top() if top else outer.top()
    below = outer.bottom() + 1 - thick if joined else inner.bottom() + 1
    if top:
        fill(painter, QRect(left, first - thick, width, thick), colour)
    fill(painter, QRect(left, below, width, thick), colour)
    fill(painter, QRect(left, first, thick, below - first), colour)
    fill(painter, QRect(right, first, thick, below - first), colour)


def rule_below(painter: QPainter, rect: QRect, colour: QColor) -> None:
    """A line along the last pixels of `rect`, touching what stands below it."""
    thick = line_width(painter)
    area = device_rect(painter, rect)
    fill(painter, QRect(area.left(), area.bottom() + 1 - thick, area.width(), thick), colour)
