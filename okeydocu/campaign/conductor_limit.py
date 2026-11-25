# OkeyDocu - okeydocu/campaign/conductor_limit.py
# What the protective conductor of a supply cable may measure, from what its element states.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A copper conductor of the stated length and cross-section has a resistance of its own; a
tenth of an ohm on top covers the contacts. On a plug that sum is the limit of the appliance
tests (EN 50678 and EN 50699, 5.3), which give a cord of up to 1.5 mm2 a fixed limit by its
length instead; a machine is not tested to them, the inspector may add them. A fixed connection
has no limit (EN 60204-1, 18.2.2; VDE 0100-600, 6.4.3.2): there the sum says what to expect."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass

LENGTH, CROSS_SECTION, MATERIAL = "cable_length", "cross_section", "conductor_material"
CONNECTION, FIXED = "supply_connection", "fixed"
COPPER = 0.0189  # ohm mm2 per metre at 30 degrees C
CONTACTS = 0.1  # ohms for the contact resistances
SMALL = 1.5  # mm2: up to here a cord has a limit by its length alone
SHORT, SHORT_LIMIT = 5.0, 0.3  # metres a cord may have for this many ohms
FURTHER, STEP, HIGHEST = 7.5, 0.1, 1.0  # each further length adds a step, up to the highest


@dataclass(frozen=True)
class ConductorLimit:
    length: float  # metres
    cross_section: float  # mm2
    conductor: float  # ohms of the conductor alone
    value: float  # ohms the reading should stay below
    by_length: bool  # the fixed limit of a cord up to 1.5 mm2
    binding: bool  # the limit of the appliance tests, not only what to expect


def _number(text: str) -> float | None:
    found = re.search(r"\d+(?:[.,]\d+)?", text or "")
    return float(found.group().replace(",", ".")) if found else None


def conductor_limit(stated: Callable[[str], str]) -> ConductorLimit | None:
    """`stated` tells what the element states for a feature key, empty where it states
    nothing. None where length or cross-section are missing or the conductor is not copper."""
    length, section = _number(stated(LENGTH)), _number(stated(CROSS_SECTION))
    if not length or not section or stated(MATERIAL).strip().lower().startswith("al"):
        return None
    conductor = COPPER * length / section
    plugged = stated(CONNECTION).strip().lower() not in ("", FIXED)
    if plugged and section <= SMALL:
        steps = math.ceil(max(length - SHORT, 0) / FURTHER)
        value = min(SHORT_LIMIT + STEP * steps, HIGHEST)
        return ConductorLimit(length, section, conductor, value, True, True)
    return ConductorLimit(length, section, conductor, conductor + CONTACTS, False, plugged)
