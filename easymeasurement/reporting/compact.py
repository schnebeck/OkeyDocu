# EasyMeasurement - easymeasurement/reporting/compact.py
# All measurements of an element in one table, whatever was measured, in the order taken.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The compact layout of a `structure` block, chosen with `layout: compact`. Each row names
its measuring function and shows what it found with the limit it was judged by. What all
measurements of one function at the element share, their settings and conditions, stands
once above the table; what differs goes into the row's remark, with the photos it refers to."""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..l10n import N_, tr
from ..model import conductor_of
from ..vocabulary import conductors as low_numbers
from ..vocabulary import function_markup, result_markup, symbols_marked
from .context import ReportMeasurement
from .footnotes import Footnotes
from .language import value_text
from .measurement_remarks import NOTE, SHARED, remark
from .measurement_table import CONDITIONS, SETTINGS, Columns, limit_text, verdict_mark
from .measurement_words import clock_times, word
from .nodes import Fields, Footnoted, Markup, Node, Table

FUNCTION = N_("Measurement")
QUESTION = "question"  # a check names what it asked instead of its function
RESULT = N_("Result")
LIMIT = N_("Limit")


def found_cell(columns: Columns, row: int) -> Markup:
    """The figures of a measurement; with more than one, each with its own symbol on a line,
    so a current direction standing for RLO says which it is."""
    found = columns.found[row]
    keys = [key for key in columns.results if key in found and key not in (NOTE, QUESTION)]
    if len(keys) == 1:
        return Markup(escape(word(found[keys[0]][0].quantity.raw)))
    lines = []
    for key in keys:
        result = found[key][0]
        lines.append(f"{result_markup(result.key, result.label)} {escape(word(result.quantity.raw))}")
    return Markup("<br/>".join(lines))


def limit_cell(columns: Columns, row: int) -> Markup:
    """Each limit on a line of its own, a lower one above an upper one, so the column stays
    narrow."""
    found = columns.found[row]
    lines = []
    for key in columns.results:
        if key in found:
            result = found[key][0]
            lines += [value_text(limit) for limit in (result.lower_limit, result.upper_limit)
                      if limit]
            lines += [limit_text(result)] if result.setpoint else []
    return Markup("<br/>".join(escape(line) for line in lines))


def _remark(columns: Columns, row: int, measurement, references: list[str]) -> Markup:
    """A check's own remark, the settings and conditions its kind does not share, then the
    remark of the measurement and its photos, each on a line of its own."""
    found, settings = columns.found[row], columns.settings[row]
    parts = [escape(word(found[NOTE][0].quantity.raw))] if NOTE in found else []
    parts += [f"{symbols_marked(name)}: {escape(settings[name])}"
              for name in columns.varying_settings if name in settings]
    parts += [f"{columns.symbol(key)} = {escape(value_text(found[key][0].quantity.raw))}"
              for key in columns.varying_conditions if key in found]
    said = remark(measurement, references)
    parts += [escape(line) for line in said.split("\n")] if said else []
    return Markup("<br/>".join(parts))


def what_cell(columns: Columns, row: int, function: str, conductor: str = "") -> Markup:
    """What was measured; between which conductors on a line below, or what a check asked."""
    found = columns.found[row]
    if QUESTION in found:
        return Markup(escape(word(found[QUESTION][0].quantity.raw)))
    what = function_markup(function, short=True)
    return Markup(f"{what}<br/>{low_numbers(conductor)}" if conductor else what)


def _head(groups: dict[str, Columns]) -> list[tuple[str, str]]:
    """One line per function with its shared settings and conditions."""
    rows = []
    for function, columns in groups.items():
        stated = columns.stated()
        parts = stated[SETTINGS] + stated[CONDITIONS]
        if parts:
            rows.append((Markup(function_markup(function, short=True)), Markup(SHARED.join(parts))))
    return rows


def compact_nodes(measured: list[ReportMeasurement], notes: Footnotes) -> list[Node]:
    groups: dict[str, list[ReportMeasurement]] = {}
    for measurement in measured:
        groups.setdefault(measurement.data.function, []).append(measurement)
    columns = {function: Columns(group) for function, group in groups.items()}
    conductors = [conductor_of(m.data.parameters) for m in measured]
    headers = [tr("No."), tr("Time"), tr(FUNCTION)]
    limited = any(limit_cell(columns[m.data.function], groups[m.data.function].index(m))
                  for m in measured)
    headers += [tr(RESULT)] + ([tr(LIMIT)] if limited else []) + ["", tr("Remark")]
    rows, photos, refs, times = [], [], [], clock_times(measured)
    for number, measurement in enumerate(measured):
        group = columns[measurement.data.function]
        row = groups[measurement.data.function].index(measurement)
        taken, references = notes.take(measurement)
        refs.append(list(range(len(photos), len(photos) + len(taken))))
        photos += taken
        cells = [str(number + 1), times[number],
                 what_cell(group, row, measurement.data.function, conductors[number])]
        cells.append(found_cell(group, row))
        cells += [limit_cell(group, row)] if limited else []
        cells += [verdict_mark(measurement.data.verdict), _remark(group, row, measurement,
                                                                  references)]
        rows.append(cells)
    head = _head(columns)
    table = Table(headers, rows, [], len(headers) - 1)
    return ([Fields(head)] if head else []) + [Footnoted(table, photos, refs)]
