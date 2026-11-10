# EasyMeasurement - easymeasurement/reporting/language.py
# The language a protocol is written in, independent of the language of the program.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A protocol speaks its own language: `speaking(code)` holds it while the protocol is
generated, so no function between template and PDF has to pass it on.

Texts of the program are English and translated with `tr`. Texts of templates, plans and
records may be written in any catalogued language, so they go through `pick`, which
recognises them in the catalogues. Template texts may also be given per language, such as
`{en: Test report, de: Prüfprotokoll}`.
"""
from __future__ import annotations

import re

from ..l10n import available, current, day, in_language, moment, speaking
from ..l10n.formats import pattern

__all__ = ["UNIT_SPACE", "current", "day", "languages", "moment", "pick", "speaking",
           "value_text"]

_NUMBER = re.compile(r"^([<>≤≥]?)\s*(-?\d+(?:[.,]\d+)?)\s*(\S*)$")
UNIT_SPACE = "\u202f"  # narrow no-break space, between a number and its unit


def languages() -> dict[str, str]:
    """Code and own name of every language a protocol can be written in."""
    return available()


def pick(value) -> str:
    """A template text, given once or per language."""
    if isinstance(value, dict):
        if value.get(current()):
            return str(value[current()])
        written = next((str(text) for text in value.values() if text), "")
        return in_language(written)
    return in_language(str(value))


def value_text(raw: str) -> str:
    """A reading as the instrument gave it, only with the decimal sign of the language and a
    narrow space that never breaks before the unit: `2.05MΩ` becomes `2,05 MΩ`. Digits,
    qualifier and unit stay as they are."""
    match = _NUMBER.match(raw.strip()) if raw else None
    if not match:
        return raw
    qualifier, number, unit = match.groups()
    number = number.replace(".", pattern("decimal")).replace(",", pattern("decimal"))
    return f"{qualifier}{number}" + (f"{UNIT_SPACE}{unit}" if unit else "")
