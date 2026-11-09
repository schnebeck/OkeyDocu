# EasyMeasurement - easymeasurement/campaign/assignment.py
# Assigns fetched measurements to plan steps by time window and function.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

# The instrument stores whole seconds and the clock offset is measured to about
# a second, so window edges get this much slack.
WINDOW_SLACK = timedelta(seconds=2)

ISSUE_OUTSIDE = "outside_window"
ISSUE_FUNCTION = "function_mismatch"

ISSUE_TEXT = {
    ISSUE_OUTSIDE: "Außerhalb jedes bestätigten Messschritts",
    ISSUE_FUNCTION: "Messfunktion passt nicht zum Schritt",
}


@dataclass(frozen=True)
class StepWindow:
    step_id: int
    opened_at: datetime
    closed_at: datetime | None
    accepted_functions: frozenset[str]


@dataclass(frozen=True)
class Assignment:
    step_id: int | None
    issue: str = ""


def assign(local_time: datetime, function: str, windows: list[StepWindow]) -> Assignment:
    """Find the step a measurement belongs to.

    A measurement is only assigned automatically when both its time and its
    function fit. Anything else stays open for the operator: a wrong automatic
    assignment in a test record is worse than a question.
    """
    in_window = [
        w
        for w in windows
        if w.opened_at - WINDOW_SLACK <= local_time
        and (w.closed_at is None or local_time <= w.closed_at + WINDOW_SLACK)
    ]
    if not in_window:
        return Assignment(None, ISSUE_OUTSIDE)
    fitting = {w.step_id for w in in_window if function in w.accepted_functions}
    if len(fitting) == 1:
        return Assignment(fitting.pop())
    return Assignment(None, ISSUE_FUNCTION if not fitting else ISSUE_OUTSIDE)
