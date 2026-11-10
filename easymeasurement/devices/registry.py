# EasyMeasurement - easymeasurement/devices/registry.py
# Maps driver names to factories, so new instruments need no application change.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..l10n import N_
from .base import FoundInstrument, MeterDriver
from .naming import InstrumentWords, SettingWords


@dataclass(frozen=True)
class DriverInfo:
    key: str
    label: str
    factory: Callable[..., MeterDriver]
    find: Callable[[], list[FoundInstrument]] | None = None
    words: InstrumentWords | None = None  # how its codes are put in words
    structure_types: dict[str, str] | None = None  # what an element is on the instrument
    instructions: object | None = None  # folder of how to set it up for each function


_DRIVERS: dict[str, DriverInfo] = {}


def register_driver(key: str, label: str, factory, find=None, words=None,
                    structure_types=None, instructions=None) -> None:
    _DRIVERS[key] = DriverInfo(key, label, factory, find, words, structure_types, instructions)


def available_drivers() -> list[DriverInfo]:
    _load_builtin()
    return list(_DRIVERS.values())


def find_instruments() -> list[FoundInstrument]:
    """Every instrument that can be chosen right now, real ones only."""
    return [found for driver in available_drivers() if driver.find for found in driver.find()]


def setting_words(db) -> SettingWords:
    """Settings in words, over every instrument that has words for its codes."""
    return SettingWords(db, [info.words for info in available_drivers() if info.words])


def structure_types() -> dict[str, str]:
    """Code and (untranslated) name of what an element can be on an instrument."""
    found: dict[str, str] = {}
    for info in available_drivers():
        found.update(info.structure_types or {})
    return found


def instruction_folders() -> list:
    """Where the drivers keep their instructions, one YAML file per function."""
    return [info.instructions for info in available_drivers() if info.instructions]


def create_driver(key: str, **options) -> MeterDriver:
    _load_builtin()
    return _DRIVERS[key].factory(**options)


def _load_builtin() -> None:
    if _DRIVERS:
        return
    from .profitest_prime import mapping
    from .profitest_prime.discovery import DRIVER_KEY, LABEL, find_instruments as find_primes
    from .profitest_prime.driver import ProfitestPrimeDriver
    from .simulator import SimulatedMeter

    words = InstrumentWords(DRIVER_KEY, mapping.is_code, mapping.culture)
    register_driver(DRIVER_KEY, LABEL, ProfitestPrimeDriver, find_primes, words,
                    mapping.STRUCTURE_TYPES, mapping.instruction_folder())
    register_driver("simulator", N_("Simulator (no hardware)"), SimulatedMeter)
