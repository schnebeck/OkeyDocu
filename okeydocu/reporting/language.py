# OkeyDocu - okeydocu/reporting/language.py
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

from ..l10n import available, current, day, in_language, moment, speaking
from ..l10n.quantities import NARROW, quantity_text
from ..vocabulary import units

__all__ = ["UNIT_SPACE", "current", "day", "languages", "moment", "pick", "speaking",
           "value_text"]

UNIT_SPACE = NARROW  # between a number and its unit


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
    """A reading as number and unit in the language of the protocol, its prefix chosen in
    steps of a thousand: `0.22Ω` becomes `220 mΩ`, `>1.20GΩ` becomes `> 1,20 GΩ`."""
    return quantity_text(raw, units())
