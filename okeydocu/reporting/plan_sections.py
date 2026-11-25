# OkeyDocu - okeydocu/reporting/plan_sections.py
# The test plans of a campaign as sections of their own, ahead of the measured quantities.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A test plan is not a measured quantity. A report ordered by quantity therefore states
first what each plan of the campaign asked and found: its answers in one table, the questions
left out with their reason and the steps without a reading. The readings of its measuring
steps stand with all others, under their quantity."""
from __future__ import annotations

from dataclasses import dataclass, field

from ..l10n import N_, plural, tr
from ..model import SIGHT_CHECK_FUNCTION
from .context import ReportMeasurement, ReportStep
from .measurement_table import group_nodes
from .nodes import Fields, Heading, Node, Paragraph

NOT_MEASURED = N_("Not measured")
LEFT_OUT = N_("Questions left out, with the reason")
NO_REASON = N_("no reason given")
READINGS_BELOW = (N_("The reading of {count} measuring step stands below, under its quantity."),
                  N_("The readings of {count} measuring steps stand below, under their"
                     " quantity."))


@dataclass
class PlanPart:
    """What one plan left behind, in the order of its steps."""

    answers: list[ReportMeasurement] = field(default_factory=list)
    left_out: list[tuple[str, str]] = field(default_factory=list)
    missing: list[tuple[str, str]] = field(default_factory=list)
    measured: int = 0  # measuring steps with a reading

    def nodes(self, title: str, options: dict, notes) -> list[Node]:
        nodes: list[Node] = [Heading(title, 2)]
        if self.answers:
            nodes.extend(group_nodes(self.answers, options, notes, points=True))
        nodes.extend(open_ends(self.left_out, self.missing, 3))
        if self.measured:
            nodes.append(Paragraph(plural(self.measured, *READINGS_BELOW)))
        return nodes


def left_out_of(step: ReportStep) -> bool:
    return step.question and step.left_out


def open_ends(left_out: list, missing: list, depth: int) -> list[Node]:
    """A question left out with its reason was not measured in any sense; it is listed apart
    from the steps that only lack their reading."""
    nodes: list[Node] = []
    if left_out:
        nodes += [Heading(tr(LEFT_OUT), depth), Fields(left_out)]
    if missing:
        nodes += [Heading(tr(NOT_MEASURED), depth), Fields(missing)]
    return nodes


def loose_ends(steps) -> tuple[list, list]:
    """The questions left out and the steps without a reading among `steps`."""
    left_out = [(step.title, step.note) for step in steps if left_out_of(step)]
    missing = [(step.title, step.note or tr(NO_REASON)) for step in steps
               if not step.measurements and not left_out_of(step)]
    return left_out, missing


def plan_parts(steps) -> dict[str, PlanPart]:
    """The steps that belong to a test plan, by the name of their plan."""
    parts: dict[str, PlanPart] = {}
    for step in steps:
        if not step.plan:
            continue
        part = parts.setdefault(step.plan, PlanPart())
        if step.function == SIGHT_CHECK_FUNCTION and step.measurements:
            part.answers.extend(step.measurements)
        elif step.measurements:
            part.measured += 1
        else:
            left_out, missing = loose_ends([step])
            part.left_out.extend(left_out)
            part.missing.extend(missing)
    return parts
