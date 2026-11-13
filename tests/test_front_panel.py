# OkeyDocu - tests/test_front_panel.py
# The drawn front panel: detents by angle, a knob that turns, parts that are pointed at.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QPointF, Qt

from okeydocu.devices.profitest_prime import panel
from okeydocu.devices.profitest_prime.selector import selector_position
from okeydocu.ui.front_panel import FrontPanel


def test_every_detent_has_a_place_in_the_drawing(qtbot):
    widget = FrontPanel(panel.DRAWING)
    qtbot.addWidget(widget)
    assert all(widget.front.elementExists(f"pos-{value}") for value in panel.VALUES)
    for part in ("socket-1", "socket-2", "socket-3", "socket-clamp", "key-start", "key-idn",
                 "soft-1", "soft-5", "led-mains", "lcd", "mains-switch", "fuse-4", "usb"):
        assert widget.front.elementExists(part), part


@pytest.mark.parametrize("value, degrees", [(35, 0), (12, 15), (18, 105), (34, 345)])
def test_a_detent_is_found_by_its_angle_and_back(value, degrees):
    assert panel.angle_of(value) == degrees
    assert panel.value_at(degrees + 6) == value
    assert panel.angle_of(11) is None


def test_the_knob_takes_the_short_way_round(qtbot):
    widget = FrontPanel(panel.DRAWING)
    qtbot.addWidget(widget)
    widget.turn_to(34)
    qtbot.waitUntil(lambda: widget._turn.state() == widget._turn.State.Stopped, timeout=3000)
    assert widget.angle == pytest.approx(-15)


def test_a_click_on_a_detent_asks_for_it(qtbot):
    widget = FrontPanel(panel.DRAWING)
    qtbot.addWidget(widget)
    widget.resize(1180, 600)
    label = widget.part_rect("pos-18").center()
    with qtbot.waitSignal(widget.position_chosen) as chosen:
        qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=label.toPoint())
    assert chosen.args == [18]
    assert selector_position(18).label == "IΔN"


def test_a_click_beside_the_dial_asks_for_nothing(qtbot):
    widget = FrontPanel(panel.DRAWING)
    qtbot.addWidget(widget)
    widget.resize(1180, 600)
    with qtbot.assertNotEmitted(widget.position_chosen):
        qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=QPointF(60, 60).toPoint())


def test_only_parts_of_the_drawing_are_pointed_at(qtbot):
    widget = FrontPanel(panel.DRAWING)
    qtbot.addWidget(widget)
    widget.point_at("key-idn", "no-such-part")
    assert widget.pointed == ("key-idn",)
    widget.point_at()
    assert widget._pulse.state() == widget._pulse.State.Stopped
