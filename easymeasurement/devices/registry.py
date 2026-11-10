# EasyMeasurement - easymeasurement/devices/registry.py
# Maps driver names to factories, so new instruments need no application change.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from .base import FoundInstrument, MeterDriver
from .driver_info import DriverInfo
from .naming import SettingWords

_DRIVERS: dict[str, DriverInfo] = {}


def register_driver(info: DriverInfo) -> None:
    _DRIVERS[info.key] = info


def available_drivers() -> list[DriverInfo]:
    _load_builtin()
    return list(_DRIVERS.values())


def driver_info(key: str) -> DriverInfo | None:
    """What a driver says about itself; None for a key no driver has (a campaign by hand)."""
    _load_builtin()
    return _DRIVERS.get(key)


def is_simulated(key: str) -> bool:
    info = driver_info(key)
    return info is not None and info.simulated


def find_instruments() -> list[FoundInstrument]:
    """Every instrument that can be chosen right now, real ones only."""
    return [found for driver in available_drivers() if driver.find for found in driver.find()]


def setting_words(db) -> SettingWords:
    """Settings in words, over every instrument that has words for its codes."""
    return SettingWords(db, [info.words for info in available_drivers() if info.words])


def instruction_folders() -> list:
    """Where the drivers keep their instructions, one YAML file per function."""
    return [info.instructions for info in available_drivers() if info.instructions]


def create_driver(key: str, **options) -> MeterDriver:
    _load_builtin()
    return _DRIVERS[key].factory(**options)


def _load_builtin() -> None:
    if _DRIVERS:
        return
    from .profitest_prime.info import DRIVER as PROFITEST_PRIME
    from .simulator import DRIVER as SIMULATOR

    register_driver(PROFITEST_PRIME)
    register_driver(SIMULATOR)
