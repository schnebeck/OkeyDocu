# EasyMeasurement - easymeasurement/vocabulary/roles.py
# What each figure of a measuring function's result stands for.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""An instrument sends the whole result block of a function, whether every figure in it
was taken or not. The vocabulary of the function says which figures tell the conditions of
the measurement, such as the lead compensation of RLO, and which count only where the
measurement did not pass, such as the two polarities of RLO. A figure without a value is
not measured. Every other figure is a result of its own."""
from __future__ import annotations

import re
from enum import Enum

from ..l10n import N_
from .terms import vocabulary

_EMPTY = re.compile(r"^[\s\-–—.]*$")


class Role(str, Enum):
    RESULT = "result"
    CONDITION = "condition"
    ON_FAIL = "on_fail"
    NOT_MEASURED = "not_measured"


ROLE_TEXT = {
    Role.RESULT: N_("Result"),
    Role.CONDITION: N_("Measuring condition"),
    Role.ON_FAIL: N_("Counts only if the measurement did not pass"),
    Role.NOT_MEASURED: N_("Not measured"),
}


def role(function: str, key: str, raw: str) -> Role:
    if _EMPTY.match(raw or ""):
        return Role.NOT_MEASURED
    term = vocabulary().functions.get(function)
    if term is not None and key in term.conditions:
        return Role.CONDITION
    if term is not None and key in term.on_fail:
        return Role.ON_FAIL
    return Role.RESULT


def counts(function: str, key: str, raw: str, passed: bool) -> bool:
    """Whether the figure belongs in a report of the measurement."""
    found = role(function, key, raw)
    if found is Role.NOT_MEASURED:
        return False
    return found is not Role.ON_FAIL or not passed
