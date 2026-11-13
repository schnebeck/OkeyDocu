# OkeyDocu - okeydocu/reporting/summary.py
# The report in brief: each element with its result, then defects and notices.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A `summary` block stands before the measurements but speaks of all of them: it lists every
element with how many measurements it had and whether they passed, then what did not pass and
the photos marked as a defect, then the photos marked as a notice. It refers to photos by the
numbers the measurements give them, so it is filled in once the whole report is laid out."""
from __future__ import annotations

from dataclasses import dataclass
from xml.sax.saxutils import escape

from ..campaign.photo_marks import ROLES
from ..l10n import N_, tr
from ..model import Verdict
from .compact import found_cell, limit_cell, what_cell
from .footnotes import NUMBERED, Footnotes, photo_texts, references
from .measurement_remarks import remark
from .measurement_table import Columns, verdict_mark
from .nodes import Heading, Markup, Node, Paragraph, Table
from .structure import report_levels

OVERVIEW = N_("Overview")
DEFECTS = N_("Defects")
NOTICES = N_("Notices")
NO_DEFECTS = N_("No defects were found.")
LEGEND = N_("✓ passed · ✗ failed · – not judged · [n] photo n of this report · symbols of"
            " quantities after ISO 80000, the index names what was measured")
ELEMENT = N_("Element")
MEASUREMENTS = N_("Measurements")


@dataclass
class SummaryPlace:
    """Where the summary goes, until the report around it is known."""

    block: dict


def _verdict(measured) -> Verdict:
    verdicts = {m.data.verdict for m in measured}
    if Verdict.FAILED in verdicts:
        return Verdict.FAILED
    return Verdict.PASSED if verdicts == {Verdict.PASSED} else Verdict.NOT_EVALUATED


def _photos(measured, role: str, notes: Footnotes) -> list[tuple]:
    """Photos of the role, with their number and the texts of their marks."""
    found = []
    for measurement in measured:
        for path in measurement.photos:
            own, marks, *_ = measurement.photo_notes.get(str(path), ("", []))
            if own == role and str(path) in notes.numbers:
                texts = photo_texts(measurement, own, marks, NUMBERED)
                found.append((notes.numbers[str(path)], "\n".join(texts)))
    return found


def numbers_text(numbers: list[int]) -> str:
    """Photo numbers as `[3]`, `[3], [4]` or, for three and more in a row, `[3]–[5]`."""
    runs: list[list[int]] = []
    for number in numbers:
        if runs and number == runs[-1][-1] + 1:
            runs[-1].append(number)
        else:
            runs.append([number])
    parts = []
    for run in runs:
        if len(run) > 2:
            parts.append(f"[{run[0]}]–[{run[-1]}]")
        else:
            parts += [f"[{number}]" for number in run]
    return ", ".join(parts)


def _merged(rows: list[tuple[str, int, str]]) -> list[list[str]]:
    """Photos of one element that say the same share a row."""
    merged: list[list] = []
    for title, number, texts in rows:
        if merged and merged[-1][0] == title and merged[-1][2] == texts:
            merged[-1][1].append(number)
        else:
            merged.append([title, [number], texts])
    return [[title, numbers_text(numbers), texts] for title, numbers, texts in merged]


def _failed_row(title: str, measurement, notes: Footnotes) -> list:
    columns = Columns([measurement])
    numbers = [(notes.numbers[str(p)], []) for p in measurement.photos if str(p) in notes.numbers]
    return [title, what_cell(columns, 0, measurement.data.function), found_cell(columns, 0),
            limit_cell(columns, 0), remark(measurement, references(numbers))]


def summary_nodes(values: dict) -> list[Node]:
    levels, notes = report_levels(values), values["_footnotes"]
    overview = [[level.title, str(len(level.measurements)), verdict_mark(_verdict(level.measurements))]
                for level in levels]
    nodes: list[Node] = [Heading(tr(OVERVIEW), 3),
                         Table([tr(ELEMENT), tr(MEASUREMENTS), ""], overview, [], 0)]
    failed = [_failed_row(level.title, m, notes) for level in levels for m in level.measurements
              if m.data.verdict is Verdict.FAILED]
    failed += [[level.title, Markup(f"<b>{escape(tr(ROLES['defect']))}</b> [{number}]"), "", "",
                texts] for level in levels for number, texts in
               _photos(level.measurements, "defect", notes)]
    nodes.append(Heading(tr(DEFECTS), 3))
    headers = [tr(ELEMENT), tr("Measurement"), tr("Result"), tr("Limit"), tr("Remark")]
    nodes.append(Table(headers, failed, [], 4) if failed else Paragraph(tr(NO_DEFECTS)))
    hints = _merged([(level.title, number, texts) for level in levels
                     for number, texts in _photos(level.measurements, "hint", notes)])
    if hints:
        nodes += [Heading(tr(NOTICES), 3), Table([tr(ELEMENT), tr("Photo"), tr("Remark")], hints,
                                                 [], 2)]
    return nodes + [Paragraph(tr(LEGEND))]
