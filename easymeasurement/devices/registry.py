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


@dataclass(frozen=True)
class DriverInfo:
    key: str
    label: str
    factory: Callable[..., MeterDriver]
    find: Callable[[], list[FoundInstrument]] | None = None


_DRIVERS: dict[str, DriverInfo] = {}


def register_driver(key: str, label: str, factory, find=None) -> None:
    _DRIVERS[key] = DriverInfo(key, label, factory, find)


def available_drivers() -> list[DriverInfo]:
    _load_builtin()
    return list(_DRIVERS.values())


def find_instruments() -> list[FoundInstrument]:
    """Every instrument that can be chosen right now, real ones only."""
    return [found for driver in available_drivers() if driver.find for found in driver.find()]


def create_driver(key: str, **options) -> MeterDriver:
    _load_builtin()
    return _DRIVERS[key].factory(**options)


def _load_builtin() -> None:
    if _DRIVERS:
        return
    from .profitest_prime.discovery import DRIVER_KEY, LABEL, find_instruments as find_primes
    from .profitest_prime.driver import ProfitestPrimeDriver
    from .simulator import SimulatedMeter

    register_driver(DRIVER_KEY, LABEL, ProfitestPrimeDriver, find_primes)
    register_driver("simulator", N_("Simulator (no hardware)"), SimulatedMeter)
