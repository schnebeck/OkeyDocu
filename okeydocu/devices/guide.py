# OkeyDocu - okeydocu/devices/guide.py
# What a guided first measurement shows, station by station, for one measuring function.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A driver describes its instrument's side of a measurement: which test lead goes into which
row of sockets, how its probe is marked and where on the test point it goes. The test point is
named by a kind of drawing, so the app can draw what the tester has in front of them."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..l10n import N_

STATIONS = (N_("Installation"), N_("Rotary switch"), N_("Test leads"), N_("Supply"),
            N_("Mode and limits"), N_("Measure"))
PLACE, DIAL, LEADS, SUPPLY, MODE, MEASURE = range(len(STATIONS))


@dataclass(frozen=True)
class Lead:
    plug: str  # marking on the plug, as on the cable
    row: str  # the socket row in the panel drawing the plug covers
    probe: str  # marking on the probe
    terminal: str  # where on the test point the probe goes
    text: str  # what the tester does, to be translated


@dataclass(frozen=True)
class Action:
    parts: tuple[str, ...]  # what the tester works with, as named in the panel drawing
    text: str  # what to do with it, to be translated


@dataclass(frozen=True)
class Guide:
    function: str
    title: str
    selector: int  # the dial position the instrument reports for it
    test_object: str  # kind of drawing of the test point
    test_point: str  # what the test point is, to be translated
    leads: tuple[Lead, ...]  # in the order the probes are placed
    caution: str = ""
    owner_feature: str = ""  # a feature the kind of element measured has, such as an RCD type
    element_features: tuple[str, ...] = ()  # what the guide needs that element to state
    live: bool = True  # whether the installation stays energised while measuring
    preparation: tuple[tuple[str, str], ...] = ()  # what to do beforehand: heading, text
    selector_label: str = ""  # the target position as printed on the dial
    selector_note: str = ""  # what the position measures, to be translated
    mains: bool = False  # whether the measurement needs the mains, not only the battery
    settings: tuple[Action, ...] = ()  # what to set before measuring
    steps: tuple[Action, ...] = ()  # how to measure and store, in order
    results: tuple[str, ...] = ()  # functions of a reading that ends the measurement
    drawing_features: tuple[str, ...] = ()  # what the drawing of the test point prints
    every_path: bool = False  # AUTO measures every pair of conductors, there or not

    def ended_by(self, function: str) -> bool:
        """Whether a reading of `function` is the result this measurement waits for."""
        return function == self.function or function in self.results


@dataclass(frozen=True)
class PanelDrawing:
    """An instrument's front panel as drawn, and where its dial is in the drawing."""

    front: object  # SVG of the panel without the knob
    knob: object  # SVG of the knob, pointing up, turning about its centre
    dial: tuple[float, float]
    knob_radius: float
    dial_reach: float  # a click this far from the centre still turns the dial
    angle_of: Callable[[int], float | None]  # reported position to degrees from the top
    value_at: Callable[[float], int]  # degrees from the top to the nearest position
