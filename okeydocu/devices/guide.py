# OkeyDocu - okeydocu/devices/guide.py
# What a guided first measurement shows, station by station, for one measuring function.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A driver describes its instrument's side of a measurement: the stations its flow runs
through, which test lead goes into which row of sockets, how its probe is marked and where on
the test point it goes. The test point is named by a kind of drawing, so the app can draw what
the tester has in front of them.

A flow is a list of stations of the kinds the application knows, in any number and order; the
first is always the element measured at. A kind new to the application is added there once and
is then open to every driver."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ..l10n import N_
from .screen import Key, Screen

PLACE, SELECT, CONNECT, PREPARE, CONFIGURE, MEASURE = (
    "place", "select", "connect", "prepare", "configure", "measure")
KIND_TITLES = {PLACE: N_("Installation"), SELECT: N_("Function"), CONNECT: N_("Test leads"),
               PREPARE: N_("Preparation"), CONFIGURE: N_("Settings"), MEASURE: N_("Measure")}


@dataclass(frozen=True)
class Lead:
    plug: str  # marking on the plug, as on the cable
    row: str  # the socket row in the panel drawing the plug covers
    probe: str  # marking on the probe
    terminal: str  # where on the test point the probe goes
    text: str  # what the tester does, to be translated


@dataclass(frozen=True)
class Action:
    """`key` names a setting by the softkey row that shows it. The softkey to press is the one
    beside that row in the view on the display; a view without the row has no such setting."""

    parts: tuple[str, ...]  # what the tester works with, as named in the panel drawing
    text: str  # what to do with it, to be translated
    key: Key | None = None


@dataclass(frozen=True)
class Station:
    """One station of a flow. `select` turns a drawn dial where the guide names a position and
    the panel has one, and otherwise lists its actions; `prepare` and `configure` list their
    actions and point at the parts they name; `zoom` closes the panel in on parts."""

    kind: str
    title: str = ""  # to be translated; empty: the kind's own name
    actions: tuple[Action, ...] = ()
    zoom: tuple[str, ...] = ()

    def heading(self) -> str:
        return self.title or KIND_TITLES[self.kind]


DEFAULT_FLOW = tuple(Station(kind) for kind in (PLACE, SELECT, CONNECT, PREPARE, CONFIGURE,
                                                 MEASURE))


@dataclass(frozen=True)
class Guide:
    function: str
    title: str
    selector: int | None  # the dial position the instrument reports for it; None: no dial
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
    settings: tuple[Action, ...] = ()  # what to set before measuring
    steps: tuple[Action, ...] = ()  # how to measure and store, in order
    screen: Screen | None = None  # the display at the guide's own dial position
    screens: tuple[tuple[int, Screen], ...] = ()  # at other positions that serve it, by value
    result_key: tuple[int, Key] | None = None  # softkey and its row once a reading stands
    results: tuple[str, ...] = ()  # functions of a reading that ends the measurement
    drawing_features: tuple[str, ...] = ()  # what the drawing of the test point prints
    every_path: bool = False  # AUTO measures every pair of conductors, there or not
    flow: tuple[Station, ...] = DEFAULT_FLOW
    variants: tuple[Variant, ...] = ()  # guides that take over for what the element states
    follow: Guide | None = None  # guided next in the same run, from where its flow begins

    def kinds(self) -> tuple[str, ...]:
        return tuple(station.kind for station in self.flow)

    def suited(self, stated: Callable[[str], str]) -> Guide:
        """The guide for an element: the first variant whose feature the element states with
        its value, as `stated` tells by feature key, or this guide itself."""
        return next((variant.guide for variant in self.variants
                     if stated(variant.feature) == variant.value), self)

    def served_at(self, value: int | None) -> bool:
        """Whether the dial position `value` serves the measurement: the guide's own, or one
        it has a view for."""
        return value == self.selector or value in dict(self.screens)

    def screen_at(self, value: int | None, measured: bool = False) -> Screen | None:
        """The view at the dial position `value`, the guide's own where that position has none;
        `measured` with a reading on it."""
        screen = dict(self.screens).get(value, self.screen)
        if screen is None or not measured or self.result_key is None:
            return screen
        return screen.with_key(*self.result_key)

    def chain(self) -> tuple[Guide, ...]:
        """This guide and those that follow it in the same run."""
        return (self, *(self.follow.chain() if self.follow is not None else ()))

    def ended_by(self, function: str) -> bool:
        """Whether a reading of `function` is the result this measurement waits for."""
        return function == self.function or function in self.results


@dataclass(frozen=True)
class Variant:
    """Where the element states `feature` as `value`, `guide` is the one to follow."""

    feature: str
    value: str
    guide: Guide


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
    display: str = ""  # the part a view of the display is drawn into
    softkeys: tuple[str, ...] = ()  # the keys beside the display, top to bottom
