# OkeyDocu - okeydocu/devices/driver_info.py
# What a driver package says about itself, so the application never imports a driver.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every text here is an untranslated English source text; the application translates it
when it shows it, from the catalogue the driver brings along."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..l10n import N_
from .base import FoundInstrument, MeterDriver
from .naming import InstrumentWords

PREPARING = N_("The instrument is being prepared for this program. Please do not disconnect it.")


@dataclass(frozen=True)
class Pairing:
    """First contact with a wireless instrument, needed once per instrument."""

    instructions: str  # what the operator does on the instrument; simple markup allowed
    pair: Callable[[str, Callable[[str], None]], str]  # PIN and progress in, port out
    default_pin: str = ""


@dataclass(frozen=True)
class Enrolment:
    """Making a sensor known to this program: the ones in reach are listed, the one chosen
    shows itself on its display, and it is kept under a name of the tester's choosing."""

    instructions: str  # simple markup allowed
    # Seconds to listen, what to tell of each sensor the moment it is heard, and whether to
    # stop early; all heard.
    scan: Callable[[float, Callable[[FoundInstrument], None], Callable[[], bool]],
                   list[FoundInstrument]]
    point_out: Callable[[str], int]  # port in; the number the sensor now shows out
    # Port, name and whether the tester has given up in; the sensor kept, or None if given up.
    enrol: Callable[[str, str, Callable[[], bool]], FoundInstrument | None]
    forget: Callable[[str], None]  # port: the sensor is no longer offered
    enrolled: Callable[[str], bool]  # port: whether the sensor is enrolled


@dataclass(frozen=True)
class DriverInfo:
    key: str  # stored with every campaign; never changes
    label: str
    factory: Callable[..., MeterDriver]
    find: Callable[[], list[FoundInstrument]] | None = None
    words: InstrumentWords | None = None  # how its codes are put in words
    instructions: object | None = None  # folder of how to set it up for each function
    pairing: Pairing | None = None
    panel: object | None = None  # its front panel as drawn, for guided measurements
    guide: Callable[[str], object] | None = None  # function key to its guide, or None
    guided: tuple[str, ...] = ()  # the functions it has a guide for
    setting_list: Callable[[object, object], object] | None = None  # view, softkey row: its list
    softkey_view: Callable[[object, object], object] | None = None  # ... or the view it switches to
    preparing: str = PREPARING  # shown while the program gets the instrument ready
    simulated: bool = False  # random readings: shown as such, never signed
    enrolment: Enrolment | None = None
    # Booked beside the instrument a campaign is opened with, never as its own source.
    companion: bool = False
    calibrated: bool = True  # False: its readings are for information only
    identity_of: Callable[[str], object] | None = None  # port to identity, without a link
    # Result key to value in, untranslated texts out: what the figures mean for the test.
    advice: Callable[[dict[str, float]], list[str]] | None = None
