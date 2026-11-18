# OkeyDocu - tests/test_switch_drawing.py
# The main switch is drawn in the position the measurement needs; live work shows its sign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QImage, QPainter

from okeydocu.ui import test_object_switch
from okeydocu.ui.switch_handle import switch_handle
from okeydocu.ui.test_objects import DRAWINGS
from okeydocu.ui.warning_sign import electricity_sign

SIZE = 200


def painted(draw) -> QImage:
    image = QImage(SIZE, SIZE, QImage.Format.Format_RGB32)
    image.fill(QColor("#ffffff"))
    painter = QPainter(image)
    try:
        draw(painter)
    finally:
        painter.end()
    return image


def is_red(colour: QColor) -> bool:
    return colour.red() > 140 and colour.green() < 110


def is_yellow(colour: QColor) -> bool:
    return colour.red() > 200 and colour.green() > 170 and colour.blue() < 90


def test_the_grip_lies_across_when_off_and_stands_upright_when_on(qtbot):
    plate = QRectF(0, 0, SIZE, SIZE)
    beyond = int(SIZE * 0.4 * 1.1)  # just outside the knob's rim, where only the grip reaches
    off = painted(lambda painter: switch_handle(painter, plate, False))
    on = painted(lambda painter: switch_handle(painter, plate, True))
    middle = SIZE // 2
    assert is_red(off.pixelColor(middle + beyond, middle))
    assert is_yellow(off.pixelColor(middle, middle + beyond))
    assert is_red(on.pixelColor(middle, middle + beyond))
    assert is_yellow(on.pixelColor(middle + beyond, middle))


def test_the_window_shows_the_position_opposite_the_grip(qtbot):
    plate = QRectF(0, 0, SIZE, SIZE)
    window = int(SIZE * 0.4 * 0.53)
    edge = int(SIZE * 0.4 * 0.36)
    middle = SIZE // 2
    off = painted(lambda painter: switch_handle(painter, plate, False))
    on = painted(lambda painter: switch_handle(painter, plate, True))
    assert is_yellow(off.pixelColor(middle - window - edge // 2 + 2, middle - 18))
    assert is_red(off.pixelColor(middle, middle - window))
    assert is_yellow(on.pixelColor(middle - 18, middle - window - edge // 2 + 2))
    assert is_red(on.pixelColor(middle - window, middle))


def test_the_electricity_sign_is_a_yellow_triangle_with_a_black_flash(qtbot):
    sign = painted(lambda painter: electricity_sign(painter, QRectF(0, 0, SIZE, SIZE)))
    assert sign.pixelColor(SIZE // 2 - 6, int(SIZE * 0.64)).lightness() < 60  # the flash
    assert is_yellow(sign.pixelColor(int(SIZE * 0.72), int(SIZE * 0.74)))
    assert sign.pixelColor(SIZE // 2, int(SIZE * 0.87)).lightness() < 60  # the lower edge
    assert sign.pixelColor(8, 8) == QColor("#ffffff")


@pytest.mark.parametrize("live", [True, False])
def test_the_main_switch_stands_as_the_measurement_needs_it(qtbot, monkeypatch, live):
    seen = []
    monkeypatch.setattr(test_object_switch, "switch_handle",
                        lambda painter, plate, on: seen.append(on))
    painted(lambda painter: DRAWINGS["main_switch"](
        painter, QRectF(0, 0, SIZE, SIZE), [], 4, False, live))
    assert seen == [live]


def test_every_test_point_takes_the_state_of_the_installation(qtbot):
    for draw in DRAWINGS.values():
        for live in (True, False):
            assert painted(lambda painter, draw=draw, live=live: draw(
                painter, QRectF(0, 0, SIZE, SIZE), ["30 mA"], 4, False, live)) is not None
