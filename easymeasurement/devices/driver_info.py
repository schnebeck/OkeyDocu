# EasyMeasurement - easymeasurement/devices/driver_info.py
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

    button: str  # may name the instrument as {instrument}
    instructions: str  # what the operator does on the instrument; simple markup allowed
    pair: Callable[[str, Callable[[str], None]], str]  # PIN and progress in, port out
    default_pin: str = ""


@dataclass(frozen=True)
class DriverInfo:
    key: str  # stored with every campaign; never changes
    label: str
    factory: Callable[..., MeterDriver]
    find: Callable[[], list[FoundInstrument]] | None = None
    words: InstrumentWords | None = None  # how its codes are put in words
    instructions: object | None = None  # folder of how to set it up for each function
    pairing: Pairing | None = None
    preparing: str = PREPARING  # shown while the program gets the instrument ready
    simulated: bool = False  # random readings: shown as such, never signed
