# OkeyDocu - okeydocu/ui/readings.py
# A measurement's figures in one line, as far as they count.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The same figures as the report shows: what was not measured stays out, and so do the
figures that count only where a measurement did not pass. Each is written as number and unit
with its prefix in steps of a thousand. "How it was measured …" shows all of them."""
from __future__ import annotations

from collections.abc import Iterable

from ..model import Verdict
from ..reporting.language import value_text
from ..vocabulary import counts, outcome_text, result_label

GAP = "   "
_FIELD, _VALUE = chr(31), chr(30)


def readings_line(function: str, verdict: str, values: Iterable[tuple[str, str, str]]) -> str:
    """`values` are key, stored label and raw text of each figure."""
    passed = verdict == Verdict.PASSED.value
    return GAP.join(f"{result_label(key, label)} {value_text(outcome_text(raw))}"
                    for key, label, raw in values if counts(function, key, raw, passed))


def stored_values(parts: str | None) -> list[tuple[str, str, str]]:
    """The figures as the search hands them over: fields and values each by a separator."""
    found = []
    for value in (parts or "").split(_VALUE):
        fields = value.split(_FIELD)
        if len(fields) == 3:
            found.append((fields[0], fields[1], fields[2]))
    return found
