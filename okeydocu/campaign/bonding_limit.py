# OkeyDocu - okeydocu/campaign/bonding_limit.py
# The resistance supplementary protective bonding may have, from the protective device.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Where the protective device cannot disconnect in time, supplementary protective bonding
keeps the touch voltage below 50 V: the resistance of the protective bonding circuit may then
be at most 50 V divided by the current that trips the protective device within 5 s
(EN 60204-1, A.1.3). A circuit-breaker trips at the upper end of its instantaneous range at
the latest, so that multiple of its rated current stands for the current; a device without
such a range, a fuse, gives no value here."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass

RATED, CHARACTERISTIC = "rated_current", "characteristic"
TOUCH_VOLTAGE = 50.0  # volts the touch voltage has to stay below
BREAKER = "breaker"  # a curve reads "breaker <lower> <upper> ...", in multiples of the rating


@dataclass(frozen=True)
class BondingLimit:
    characteristic: str
    rated: float  # amperes
    multiple: float  # of the rated current, at which the device trips at the latest
    value: float  # ohms the protective bonding circuit may have

    @property
    def current(self) -> float:
        return self.rated * self.multiple


def _number(text: str) -> float | None:
    found = re.search(r"\d+(?:[.,]\d+)?", text or "")
    return float(found.group().replace(",", ".")) if found else None


def tripping_multiple(curve: str) -> float | None:
    """The upper end of the instantaneous range a curve names, or None."""
    parts = curve.split()
    if len(parts) < 3 or parts[0] != BREAKER:
        return None
    upper = _number(parts[2])
    return upper if upper and upper > 1 else None


def bonding_limit(stated: Callable[[str], str],
                  curve_of: Callable[[str], str]) -> BondingLimit | None:
    """`stated` tells what the element states for a feature key, `curve_of` the curve of a
    characteristic. None where rated current or characteristic are missing or the
    characteristic has no instantaneous range."""
    characteristic, rated = stated(CHARACTERISTIC).strip(), _number(stated(RATED))
    multiple = tripping_multiple(curve_of(characteristic)) if characteristic else None
    if not rated or not multiple:
        return None
    return BondingLimit(characteristic, rated, multiple, TOUCH_VOLTAGE / (rated * multiple))
