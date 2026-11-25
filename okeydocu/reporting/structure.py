# OkeyDocu - okeydocu/reporting/structure.py
# Measurements ordered by the structure of the installation they were taken at.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every element of the installation that has measurements is a level of the report, in the
order of the structure tree: the inspected installation first, then each element below it.
A `structure` block lists them in one of two orders; ordered by place, `layout: compact` puts
all measurements of an element into one table:

    place     each level, and within it every function measured there
    function  each function, and within it every level where it was measured

Each function at a level is a block of its own, which states first what its measurements
share. Ordered by function, the test plans of the campaign come first, each with its answers
and what it left open; ordered by place, steps of a plan that found no measurement follow at
the end with their reasons."""
from __future__ import annotations

from ..l10n import N_, tr
from ..vocabulary import function_markup
from .compact import compact_nodes
from .context import ReportMeasurement
from .levels import REMARK, Level
from .measurement_table import Columns, group_nodes
from .nodes import Fields, Heading, Markup, Node
from .plan_sections import loose_ends, open_ends, plan_parts

ORDERS = {"place": N_("By element of the installation"),
          "function": N_("By measured quantity, then by element"),
          "function_time": N_("By measured quantity, then by time")}


def report_levels(values: dict) -> list[Level]:
    """Without a stored structure, as in a preview, everything was taken at the installation."""
    if values.get("structure") is not None:
        return values["structure"]
    measured = [m for step in values.get("steps", ()) for m in step.measurements]
    title = values.get("asset", {}).get("name", "")
    return [Level(None, title, measurements=measured)] if measured else []


def _by_function(measurements: list[ReportMeasurement]) -> dict[str, list[ReportMeasurement]]:
    groups: dict[str, list[ReportMeasurement]] = {}
    for measurement in measurements:
        groups.setdefault(measurement.data.function, []).append(measurement)
    return groups


def _heading(level: Level, depth: int) -> Heading:
    return Heading(f"{level.title} ({level.kind})" if level.kind else level.title, depth)


def structure_nodes(block: dict, values: dict) -> list[Node]:
    levels = report_levels(values)
    notes = values["_footnotes"]
    options = block.get("many", {})
    nodes: list[Node] = []
    order = block.get("order", "place")
    steps = values.get("steps", ())
    if order in ("function", "function_time"):
        parts = plan_parts(steps)
        for title, part in parts.items():
            nodes.extend(part.nodes(title, options, notes))
        answers = {id(m) for part in parts.values() for m in part.answers}
        steps = [step for step in steps if not step.plan]  # the others are said above
        everything = sorted((m for level in levels for m in level.measurements
                             if id(m) not in answers), key=lambda m: m.local_time)
        functions = _by_function(everything)
        for function, everywhere in functions.items():
            nodes.append(Heading(Markup(function_markup(function)), 2))
            if order == "function_time":
                # One table for the whole installation, as measured; each row names its place.
                nodes.extend(group_nodes(everywhere, options, notes, points=True))
                continue
            # What every level shares is said once, under the function.
            shared = Columns(everywhere)
            nodes += [Fields(shared.head())] if shared.head() else []
            for level in levels:
                group = [m for m in level.measurements if m.data.function == function]
                if group:
                    nodes.append(_heading(level, 3))
                    if level.remark and block.get("features", True):
                        nodes.append(Fields([(tr(REMARK), level.remark)]))
                    nodes.extend(group_nodes(group, options, notes, shared.stated(), points=True))
    else:
        for level in levels:
            nodes.append(_heading(level, 2))
            if level.card and block.get("features", True):
                nodes.append(Fields(level.card))
            if block.get("layout") == "compact":
                nodes.extend(compact_nodes(level.measurements, notes))
                continue
            for function, group in _by_function(level.measurements).items():
                nodes.append(Heading(Markup(function_markup(function)), 3))
                nodes.extend(group_nodes(group, options, notes, points=True))
    return nodes + open_ends(*loose_ends(steps), 2)
