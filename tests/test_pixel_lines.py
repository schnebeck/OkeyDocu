# OkeyDocu - tests/test_pixel_lines.py
# Frames and rules stay whole and one pixel thick in a window scaled by a fraction.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QImage, QPainter

from okeydocu.ui.pixel_lines import frame, rule_below

PAPER, INK = QColor("white"), QColor("black")
SCALES = (1.0, 1.25, 1.5, 1.75, 2.0)
PLACES = tuple((x, y) for x in range(4) for y in range(4))


def painted(scale: float, place: tuple[int, int], draw, size=(40, 24)) -> tuple[QImage, QRect]:
    """What a widget of `size` standing at `place` paints with `draw`, clipped as a widget
    is; with it the pixels of the image that are the widget's own."""
    image = QImage(round(60 * scale), round(40 * scale), QImage.Format.Format_RGB32)
    image.setDevicePixelRatio(scale)
    image.fill(PAPER)
    rect = QRect(0, 0, *size)
    painter = QPainter(image)
    painter.translate(*place)
    painter.setClipRect(rect)
    draw(painter, rect, INK)
    painter.end()
    left, top = int(place[0] * scale + 0.5), int(place[1] * scale + 0.5)
    right = int((place[0] + size[0]) * scale + 0.5)
    bottom = int((place[1] + size[1]) * scale + 0.5)
    return image, QRect(left, top, right - left, bottom - top)


def dark_rows(image: QImage, x: int) -> list[int]:
    return [y for y in range(image.height()) if image.pixelColor(x, y) == INK]


def dark_columns(image: QImage, y: int) -> list[int]:
    return [x for x in range(image.width()) if image.pixelColor(x, y) == INK]


def run(values: list[int]) -> bool:
    return bool(values) and values == list(range(values[0], values[-1] + 1))


@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("place", PLACES)
def test_a_frame_is_closed_wherever_the_widget_stands(qapp, scale, place):
    image, own = painted(scale, place, frame)
    middle_x, middle_y = own.center().x(), own.center().y()
    upright, level = dark_columns(image, middle_y), dark_rows(image, middle_x)
    thick = max(1, int(scale))
    # Two lines of one thickness cross the middle either way, inside the widget's pixels.
    assert len(upright) == len(level) == 2 * thick
    assert own.left() <= upright[0] and upright[-1] <= own.right()
    assert own.top() <= level[0] and level[-1] <= own.bottom()
    # Each side runs unbroken from one corner to the other.
    for x in (upright[0], upright[-1]):
        assert dark_rows(image, x) == list(range(level[0], level[-1] + 1))
    for y in (level[0], level[-1]):
        assert dark_columns(image, y) == list(range(upright[0], upright[-1] + 1))


@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("place", PLACES)
def test_what_fills_the_inside_reaches_the_frame(qapp, scale, place):
    image, _ = painted(scale, place, frame)
    inside, _ = painted(scale, (place[0] + 1, place[1] + 1),
                        lambda painter, rect, colour: painter.fillRect(rect, colour),
                        size=(38, 22))
    row = image.height() // 2
    frame_columns, filled = dark_columns(image, row), dark_columns(inside, row)
    assert run(sorted(set(frame_columns) | set(filled)))
    assert not set(frame_columns) & set(filled)


@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("place", PLACES)
def test_blocks_standing_on_each_other_share_one_frame(qapp, scale, place):
    image = QImage(round(60 * scale), round(60 * scale), QImage.Format.Format_RGB32)
    image.setDevicePixelRatio(scale)
    image.fill(PAPER)
    painter = QPainter(image)
    painter.translate(*place)
    for row, (top, joined) in enumerate(((True, True), (False, True), (False, False))):
        rect = QRect(0, 0, 40, 15)
        painter.save()
        painter.translate(0, 15 * row)
        painter.setClipRect(rect)
        frame(painter, rect, INK, top, joined)
        painter.restore()
    painter.end()
    thick = max(1, int(scale))
    level = dark_rows(image, image.width() // 3)
    upright = dark_columns(image, (level[0] + level[-1]) // 2 + thick)
    # The line above, one below each of the two upper blocks, the line below: four in all.
    assert len(level) == 4 * thick and len(upright) == 2 * thick
    # The sides run unbroken from the first line to the last.
    for x in (upright[0], upright[-1]):
        assert dark_rows(image, x) == list(range(level[0], level[-1] + 1))


@pytest.mark.parametrize("scale", SCALES)
@pytest.mark.parametrize("place", PLACES)
def test_a_rule_lies_on_the_last_pixels_of_its_bar(qapp, scale, place):
    image, own = painted(scale, place, rule_below)
    rows = dark_rows(image, own.center().x())
    thick = max(1, int(scale))
    assert rows == list(range(own.bottom() + 1 - thick, own.bottom() + 1))
    assert dark_columns(image, rows[0]) == list(range(own.left(), own.right() + 1))
