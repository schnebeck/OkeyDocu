# OkeyDocu - okeydocu/reporting/measurement_remarks.py
# The remark of each measurement in a block: what it says, its photos and figures without a column.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A remark gathers what restricted or explained a measurement: its comment, the notes and
documents attached to it and the photos it refers to. Figures that get no column of their own
join it, each with its symbol. `columns` is the `Columns` of the block's table."""
from __future__ import annotations

from xml.sax.saxutils import escape

from ..l10n import tr
from ..vocabulary import stands_for
from .context import ReportMeasurement
from .footnotes import Footnotes
from .measurement_words import word
from .nodes import Markup

SHARED = " · "
NOTE = "note"  # a figure that is itself a remark, as with answers to a check


def remark(measurement: ReportMeasurement, references: list[str]) -> str:
    texts = [measurement.data.comment, *measurement.attached.notes,
             *(f"{tr('Attachment')} {name}" for name in measurement.attached.documents),
             *references]
    return "\n".join(text.strip() for text in texts if text and text.strip())


def referred(group: list[ReportMeasurement], notes: Footnotes) -> tuple[list, list, list]:
    """The photos of the rows, which rows refer to which, and each row's remark."""
    photos, refs, remarks = [], [], []
    for measurement in group:
        taken, references = notes.take(measurement)
        refs.append(list(range(len(photos), len(photos) + len(taken))))
        photos += taken
        remarks.append(remark(measurement, references))
    return photos, refs, remarks


def join_notes(columns, remarks: list[str]) -> None:
    """A figure that is itself a remark, as with a check, shares the column of remarks."""
    if NOTE not in columns.results:
        return
    for number, found in enumerate(columns.found):
        if NOTE in found:
            said = word(found[NOTE][0].quantity.raw)
            remarks[number] = f"{said}\n{remarks[number]}" if remarks[number] else said
    columns.results.remove(NOTE)


def move_sparse(columns, remarks: list[str]) -> list[Markup]:
    """A figure fewer than half the rows have, or one that is named beside the figure it
    stands for, is no column of its own: it joins the remark of the rows that have it, with
    its symbol, such figures on one line. Each remark becomes markup, a line per part."""
    sparse = [key for key in columns.results
              if stands_for(key) in columns.results
              or sum(key in found for found in columns.found) * 2 < len(columns.found)]
    for key in sparse:
        columns.results.remove(key)
    marked = []
    for found, said in zip(columns.found, remarks):
        figures = SHARED.join(f"{columns.symbol(key)} = {escape(word(found[key][0].quantity.raw))}"
                              for key in sparse if key in found)
        parts = ([figures] if figures else []) + [escape(line) for line in said.split("\n") if line]
        marked.append(Markup("<br/>".join(parts)))
    return marked
