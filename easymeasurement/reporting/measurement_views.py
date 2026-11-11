# EasyMeasurement - easymeasurement/reporting/measurement_views.py
# Presents measurements as document nodes: fields for one, a block with a table for several.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from xml.sax.saxutils import escape

from ..campaign.photo_marks import ROLES
from ..l10n import in_language, tr
from ..model import conductor_of
from ..vocabulary import conductors, function_markup, symbols_marked
from .context import VERDICT_TEXT, ReportStep
from .footnotes import Footnotes
from .measurement_remarks import remark
from .measurement_table import Columns, group_nodes, limit_text
from .measurement_words import when, word
from .nodes import Fields, Footnoted, Markup, Node, Photos

__all__ = ["group_nodes", "place_nodes", "remaining_photos", "scope", "single"]


def scope(values: dict) -> ReportStep:
    """Inside a repeat a block sees its step; outside it, the whole campaign."""
    step = values.get("step")
    if step is not None:
        return step
    everything = [m for s in values["steps"] for m in s.measurements]
    return ReportStep("", "", "done", "", everything)


def remaining_photos(step: ReportStep, notes: Footnotes) -> list[tuple]:
    """Photos no measurement has shown yet. Each names its measurement, so it can be traced
    like any other value; a defect or a hint says so first, the texts of the marks follow."""
    items = []
    for m in step.measurements:
        for path in m.photos:
            if str(path) in notes.shown:
                continue
            notes.shown.add(str(path))
            role, marks, *view = m.photo_notes.get(str(path), ("", []))
            caption = f"{function_markup(m.data.function)} · {escape(when(m))}"
            if role:
                caption = f"<b>{escape(tr(ROLES[role]))}:</b> {caption}"
            texts = [f"({mark.number}) {mark.text}" for mark in marks if mark.text]
            items.append((path, Markup(caption), marks, role, texts, *view))
    return items


def single(measurement, options: dict, notes: Footnotes) -> Footnoted:
    """One measurement reads like a form; its photos follow it."""
    data = measurement.data
    columns = Columns([measurement])
    rows = [(tr("Time"), when(measurement))]
    if conductor_of(data.parameters):
        rows.append((tr("Conductors"), Markup(conductors(conductor_of(data.parameters)))))
    if data.location and options.get("location", True):
        rows.append((tr("Location in the equipment"), " / ".join(data.location[1:] or data.location)))
    rows += [(Markup(symbols_marked(name)), Markup(conductors(value)))
             for name, value in measurement.settings]
    for key in columns.results + list(columns.shared_conditions):
        result = columns.found[0][key][0]
        limit = limit_text(result)
        shown = word(result.quantity.raw)
        rows.append((columns.symbol(key), f"{shown}  ({tr('limit')} {limit})" if limit else shown))
    if data.results:
        rows.append((tr("Verdict"), tr(VERDICT_TEXT[data.verdict])))
    photos, references = notes.take(measurement)
    said = remark(measurement, references)
    if said:
        rows.append((tr("Remark"), said))
    refs = [[] for _ in rows]
    refs[-1] = list(range(len(photos)))
    return Footnoted(Fields(rows), photos, refs)


def place_nodes(places: list) -> list[Node]:
    attachment = tr("Attachment")
    rows = [(in_language(p.name), note) for p in places for note in p.attached.notes]
    rows += [(in_language(p.name), f"{attachment} {name}")
             for p in places for name in p.attached.documents]
    images = [(path, in_language(p.name)) for p in places for path in p.attached.images]
    return ([Fields(rows)] if rows else []) + ([Photos(images)] if images else [])
