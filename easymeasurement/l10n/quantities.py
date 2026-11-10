# EasyMeasurement - easymeasurement/l10n/quantities.py
# A reading written as number and unit, with a prefix in steps of a thousand.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""An instrument writes `0.22Ω`, `519V` or `>1.20GΩ`. A report writes the number between 1
and 999 with one of the prefixes p, n, µ, m, k, M, G and T, a narrow space that never breaks
before the unit, the decimal sign of the language and a true minus: `220 mΩ`, `519 V`,
`> 1,20 GΩ`. Only the decimal point moves, so no digit is added or rounded away; zero keeps
the prefix it came with. A unit without a known base, such as `%` or `mV/mA`, keeps its
number as it is."""
from __future__ import annotations

import re
from decimal import Decimal

from .formats import pattern

NARROW = " "  # narrow no-break space
MINUS = "−"
PREFIXES = {"p": -12, "n": -9, "µ": -6, "m": -3, "": 0, "k": 3, "M": 6, "G": 9, "T": 12}
_BY_POWER = {power: prefix for prefix, power in PREFIXES.items()}
_SPELLING = str.maketrans({"Ω": "Ω", "μ": "µ", "u": "µ"})
_READING = re.compile(r"^([<>≤≥]?)\s*([-−]?)(\d+(?:[.,]\d+)?)\s*(\S*)$")


def _split(unit: str, bases: tuple[str, ...]) -> tuple[str, str] | None:
    """Prefix and base unit, or None for a unit that is not built so."""
    for base in bases:
        if unit == base:
            return "", base
        head = unit[: -len(base)].translate(_SPELLING)
        if unit.endswith(base) and head in PREFIXES:
            return head, base
    return None


def _shifted(number: Decimal, power: int) -> tuple[Decimal, int]:
    """The number brought between 1 and 999 by steps of a thousand, with its new power."""
    while abs(number) >= 1000 and power + 3 in _BY_POWER:
        number, power = number.scaleb(-3), power + 3
    while abs(number) < 1 and power - 3 in _BY_POWER:
        number, power = number.scaleb(3), power - 3
    return number, power


def quantity_text(raw: str, bases: tuple[str, ...]) -> str:
    """`bases` are the units prefixes may stand before, longest first."""
    match = _READING.match((raw or "").strip())
    if not match:
        return raw
    qualifier, sign, digits, unit = match.groups()
    number = Decimal(digits.replace(",", "."))
    split = _split(unit.translate({0x2126: 0x03A9}), bases) if unit else None
    if split is not None and number != 0:
        prefix, base = split
        number, power = _shifted(number, PREFIXES[prefix])
        unit = _BY_POWER[power] + base
    elif split is not None:
        unit = split[0] + split[1]
    # Fixed-point keeps every written zero and never shows an exponent.
    text = format(number, "f").replace(".", pattern("decimal"))
    if sign:
        text = MINUS + text
    if qualifier:
        text = f"{qualifier}{NARROW}{text}"
    return f"{text}{NARROW}{unit}" if unit else text
