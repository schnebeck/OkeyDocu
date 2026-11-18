# OkeyDocu - okeydocu/campaign/expected_voltage.py
# The voltage to expect between two conductors, and the readings that do not fit it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Between two line conductors stands the voltage of the system, between a line conductor and
N or PE that voltage divided by the square root of three: 400 V and 230 V unless the element
states another nominal voltage. With one line conductor the element's nominal voltage is the
one against N. A reading within a tenth of what is expected fits; N against PE is not judged."""

from __future__ import annotations

import math
import re

from ..model import MeterMeasurement, Quantity, conductor_of

BETWEEN_LINES = 400.0
TOLERANCE = 0.10
PATHS = {"u_ln": "L-N", "u_lpe": "L-PE", "u_l1l2": "L1-L2", "u_l2l3": "L2-L3",
         "u_l3l1": "L3-L1"}
PLAIN = "u"  # a voltage told by the measuring path of its measurement


def between_lines(lines: str, nominal: str) -> float:
    """The voltage between two line conductors for an element stating `lines` line conductors
    and a `nominal` voltage such as “400 V”; either may be empty."""
    stated = Quantity.parse(nominal.replace(" ", "")) if nominal else None
    if stated is None or not stated.base_value or stated.base_unit != "V":
        return BETWEEN_LINES
    return stated.base_value * math.sqrt(3) if lines == "1" else stated.base_value


def expected(path: str, system: float = BETWEEN_LINES) -> float | None:
    """What to expect between the conductors of `path`, such as L1-L2 or L-PE; None where
    nothing is expected, as between N and PE."""
    parts = re.split(r"[-+]", path)
    lines = [part for part in parts if part.startswith("L")]
    if len(lines) == 2:
        return system
    if len(lines) == 1 and len(parts) == 2:
        return system / math.sqrt(3)
    return None


def misfits(measurement: MeterMeasurement, system: float = BETWEEN_LINES) -> list[tuple]:
    """The voltages of a measurement off what is expected, as (label, reading, expected)."""
    found = []
    for result in measurement.results:
        path = (conductor_of(measurement.parameters) if result.key == PLAIN
                else PATHS.get(result.key, ""))
        wanted = expected(path, system) if path else None
        value = result.quantity.base_value
        if wanted is None or value is None or result.quantity.base_unit != "V":
            continue
        if abs(value - wanted) > wanted * TOLERANCE:
            found.append((result.label, result.quantity.raw, wanted))
    return found
