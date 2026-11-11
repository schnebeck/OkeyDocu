# EasyMeasurement - easymeasurement/reporting/measurement_table.py
# Measurements of one function as a block: what they share above, what differs in a table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A block states first what all its measurements share: the instrument's settings, the
conditions they were taken under and their limits. The table below lists each measurement
with only what differs and what it found. Figures the vocabulary calls conditions join the
settings; figures that count only where a measurement did not pass get a column only when
one did not. A remark says what restricted or explained a measurement and which photos and
notes in them belong to it."""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..l10n import N_, tr
from ..model import Verdict, conductor_of
from ..vocabulary import Role, counts, result_markup, role, symbols_marked
from ..vocabulary import conductors as low_numbers
from .context import ReportMeasurement
from .footnotes import Footnotes
from .language import value_text
from .measurement_words import marks, word
from .nodes import Fields, Footnoted, Markup, Node, Table

CONDUCTORS = N_("Conductors")
LOCATION = N_("Measuring location")
POINT = N_("Test point")
SETTINGS, CONDITIONS, LIMITS = N_("Settings"), N_("Conditions"), N_("Limits")
SHARED = " · "
NOTE = "note"  # a figure that is itself a remark, as with answers to a check
SUMMED = 3  # rows from which a table gets its minimum and maximum


def figures(measurement: ReportMeasurement) -> dict[str, tuple]:
    """Each figure that counts, by key: the result and its role."""
    data = measurement.data
    passed = data.verdict is Verdict.PASSED
    return {result.key: (result, role(data.function, result.key, result.quantity.raw))
            for result in data.results
            if counts(data.function, result.key, result.quantity.raw, passed)}


def limit_text(result) -> str:
    setpoint = f"{tr('expected')} {word(result.setpoint)}" if result.setpoint else ""
    limits = (value_text(result.lower_limit), value_text(result.upper_limit), setpoint)
    return " ".join(part for part in limits if part)


def _shared(values: list[str | None], present: bool = False) -> str | None:
    """The one value every measurement has, or None; with `present`, every measurement that
    has the figure at all, as with a limit of a figure that counts only in some rows."""
    if present:
        values = [value for value in values if value is not None]
    return values[0] if values and values[0] and all(v == values[0] for v in values) else None


class Columns:
    """Which figures, settings and limits the block states once and which each row shows."""

    def __init__(self, group: list[ReportMeasurement]):
        self.found = [figures(m) for m in group]
        self.settings = [dict(m.settings) for m in group]
        keys = list(dict.fromkeys(key for found in self.found for key in found))
        self.labels = {key: next(f[key][0] for f in self.found if key in f) for key in keys}
        conditions = [k for k in keys if self._role(k) is Role.CONDITION]
        names = list(dict.fromkeys(name for found in self.settings for name in found))
        self.shared_settings = {n: _shared([s.get(n) for s in self.settings]) for n in names}
        self.shared_conditions = {k: _shared([self._raw(f, k) for f in self.found])
                                  for k in conditions}
        self.results = [k for k in keys if k not in conditions]
        self.shared_limits = {k: _shared([limit_text(f[k][0]) if k in f else None
                                          for f in self.found], present=True)
                              for k in self.results}
        self.varying_settings = [n for n, v in self.shared_settings.items() if v is None]
        self.varying_conditions = [k for k, v in self.shared_conditions.items() if v is None]

    def _role(self, key: str) -> Role:
        return next(f[key][1] for f in self.found if key in f)

    @staticmethod
    def _raw(found: dict, key: str) -> str | None:
        return found[key][0].quantity.raw if key in found else None

    def symbol(self, key: str) -> Markup:
        result = self.labels[key]
        return Markup(result_markup(result.key, result.label))

    def stated(self) -> dict[str, list[str]]:
        """What all measurements share, by kind, each part marked up."""
        return {
            SETTINGS: [f"{symbols_marked(n)}: {low_numbers(v)}"
                       for n, v in self.shared_settings.items() if v],
            CONDITIONS: [f"{self.symbol(k)} = {escape(value_text(v))}"
                         for k, v in self.shared_conditions.items() if v],
            LIMITS: [f"{self.symbol(k)} {escape(v)}" for k, v in self.shared_limits.items() if v],
        }

    def head(self, known: dict | None = None) -> list[tuple[str, Markup]]:
        """Rows of a field list with what is shared and not `known` from a block above."""
        rows = []
        for label, parts in self.stated().items():
            new = [part for part in parts if part not in (known or {}).get(label, ())]
            if new:
                rows.append((tr(label), Markup(SHARED.join(new))))
        return rows


VERDICT_MARKS = {Verdict.PASSED: ("✓", "#1e7b45"), Verdict.FAILED: ("✗", "#a4262c"),
                 Verdict.NOT_EVALUATED: ("–", "")}


def verdict_mark(verdict: Verdict) -> Markup:
    """A tick or a cross in the colour of the result; a dash where nothing was judged."""
    sign, colour = VERDICT_MARKS[verdict]
    return Markup(f'<font color="{colour}"><b>{sign}</b></font>' if colour else sign)


def _cell(found: dict, key: str, with_limit: bool) -> str:
    if key not in found:
        return "–"
    result = found[key][0]
    shown = word(result.quantity.raw)
    limit = limit_text(result) if with_limit else ""
    return f"{shown} ({limit})" if limit else shown


def remark(measurement: ReportMeasurement, references: list[str]) -> str:
    texts = [measurement.data.comment, *measurement.attached.notes,
             *(f"{tr('Attachment')} {name}" for name in measurement.attached.documents),
             *references]
    return "\n".join(text.strip() for text in texts if text and text.strip())


def _referred(group: list[ReportMeasurement], notes: Footnotes) -> tuple[list, list, list]:
    """The photos of the rows, which rows refer to which, and each row's remark."""
    photos, refs, remarks = [], [], []
    for measurement in group:
        taken, references = notes.take(measurement)
        refs.append(list(range(len(photos), len(photos) + len(taken))))
        photos += taken
        remarks.append(remark(measurement, references))
    return photos, refs, remarks


def _join_notes(columns: Columns, remarks: list[str]) -> None:
    """A figure that is itself a remark, as with a check, shares the column of remarks."""
    if NOTE not in columns.results:
        return
    for number, found in enumerate(columns.found):
        if NOTE in found:
            said = word(found[NOTE][0].quantity.raw)
            remarks[number] = f"{said}\n{remarks[number]}" if remarks[number] else said
    columns.results.remove(NOTE)


def _differing(texts: list[str]) -> list[str]:
    return texts if len(set(texts)) > 1 else []


def group_nodes(group: list[ReportMeasurement], options: dict, notes: Footnotes,
                known: dict | None = None, points: bool = False) -> list[Node]:
    """`known` is what a block above already stated, so this block leaves it out. With
    `points`, the steps of the plan the measurements were taken for are named."""
    columns = Columns(group)
    conductors = [conductor_of(m.data.parameters) for m in group]
    places = _differing([m.data.location[-1] if m.data.location else "" for m in group])
    named = _differing([m.point for m in group]) if points else []
    photos, refs, remarks = _referred(group, notes)
    _join_notes(columns, remarks)
    leading = [tr("No."), tr("Time")] + ([tr(POINT)] if named else [])
    leading += [tr(LOCATION)] if places else []
    leading += [tr(CONDUCTORS)] if any(conductors) else []
    leading += [Markup(symbols_marked(name)) for name in columns.varying_settings]
    leading += [columns.symbol(k) for k in columns.varying_conditions]
    # The verdict speaks for itself and needs no title; every table has room for remarks,
    # so the blocks of a report look alike.
    trailing = ["", tr("Remark")]
    headers = leading + [columns.symbol(k) for k in columns.results] + trailing
    rows = []
    for number, measurement in enumerate(group, 1):
        found = columns.found[number - 1]
        cells = [str(number), measurement.local_time.strftime("%H:%M:%S") + marks(measurement)]
        cells += [named[number - 1] or "–"] if named else []
        cells += [places[number - 1] or "–"] if places else []
        cells += [Markup(low_numbers(conductors[number - 1] or "–"))] if any(conductors) else []
        cells += [Markup(low_numbers(columns.settings[number - 1].get(n, "–")))
                  for n in columns.varying_settings]
        cells += [_cell(found, k, False) for k in columns.varying_conditions]
        cells += [_cell(found, k, columns.shared_limits[k] is None) for k in columns.results]
        cells.append(verdict_mark(measurement.data.verdict))
        cells.append(remarks[number - 1])
        rows.append(cells)
    summary = []
    if options.get("summary", True) and len(group) >= SUMMED and len(set(conductors)) <= 1:
        summary = _summary(columns, len(leading), len(trailing))
    head = columns.head(known)
    if points and group[0].point and not named:
        head.insert(0, (tr(POINT), group[0].point))
    table = Table(headers, rows, summary, len(headers) - 1)
    return ([Fields(head)] if head else []) + [Footnoted(table, photos, refs)]


def _summary(columns: Columns, before: int, after: int) -> list[list[str]]:
    """Min and max of each figure that is a number; nothing where none is."""
    lines, any_number = [], False
    for label, pick in ((N_("Min"), min), (N_("Max"), max)):
        cells = [tr(label)] + [""] * (before - 1)
        for key in columns.results:
            numeric = [f[key][0] for f in columns.found
                       if key in f and f[key][0].quantity.base_value is not None]
            any_number = any_number or bool(numeric)
            cells.append(word(pick(numeric, key=lambda r: r.quantity.base_value).quantity.raw)
                         if numeric else "")
        lines.append(cells + [""] * after)
    return lines if any_number else []
