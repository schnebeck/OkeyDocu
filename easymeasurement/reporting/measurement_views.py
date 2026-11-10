# EasyMeasurement - easymeasurement/reporting/measurement_views.py
# Presents measurements as document nodes: fields for one, a table for several.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations


from ..campaign.photo_marks import ROLES
from ..model import check_text, conductor_of
from .context import VERDICT_TEXT, ReportMeasurement, ReportStep, function_label
from .language import moment, tr, value_text
from .nodes import Fields, Node, Paragraph, Photos, Table


def _scope(values: dict) -> ReportStep:
    """Inside a repeat a block sees its step; outside it, the whole campaign."""
    step = values.get("step")
    if step is not None:
        return step
    everything = [m for s in values["steps"] for m in s.measurements]
    return ReportStep("", "", "done", "", everything)


def _step_photos(step: ReportStep) -> list[tuple]:
    """Each photo names its measurement, so it can be traced like any other value.

    A defect or a hint says so first; the texts of the marks follow by their numbers.
    """
    items = []
    for m in step.measurements:
        for path in m.photos:
            role, marks = m.photo_notes.get(str(path), ("", []))
            caption = f"{function_label(m.data.function)} · {_time(m)}"
            if role:
                caption = f"{tr(ROLES[role])}: {caption}"
            texts = [f"({mark.number}) {mark.text}" for mark in marks if mark.text]
            if texts:
                caption += "".join(f"\n{text}" for text in texts)
            items.append((path, caption, marks, role))
    return items


def _marks(measurement: ReportMeasurement) -> str:
    """A record must not look measured or untouched if it is not."""
    marks = [tr(text) for flag, text in ((measurement.manual, "manuell"),
                                         (measurement.edited, "geändert")) if flag]
    return f" ({', '.join(marks)})" if marks else ""


def _word(text: str) -> str:
    """A reading in the protocol's language: neutral words such as yes or right are
    translated, numbers get its decimal sign."""
    return value_text(tr(check_text(text)))


def _time(measurement: ReportMeasurement) -> str:
    return moment(measurement.local_time, seconds=True) + _marks(measurement)


def _limit(result) -> str:
    setpoint = f"{tr('Soll')} {_word(result.setpoint)}" if result.setpoint else ""
    limits = (value_text(result.lower_limit), value_text(result.upper_limit), setpoint)
    return " ".join(part for part in limits if part)


def _single(measurement: ReportMeasurement, options: dict) -> Fields:
    data = measurement.data
    rows = [(tr("Zeitpunkt"), _time(measurement))]
    if conductor_of(data.parameters):
        rows.append((tr("Leiter"), conductor_of(data.parameters)))
    if data.location and options.get("location", True):
        rows.append((tr("Messort im Gerät"), " / ".join(data.location[1:] or data.location)))
    for result in data.results:
        limit = _limit(result)
        shown = _word(result.quantity.raw)
        rows.append((tr(result.label), f"{shown}  ({tr('Grenzwert')} {limit})" if limit else shown))
    if measurement.photos:
        rows.append((tr("Fotos"), str(len(measurement.photos))))
    if data.results:
        rows.append((tr("Bewertung"), tr(VERDICT_TEXT[data.verdict])))
    if data.comment:
        rows.append((tr("Kommentar"), data.comment))
    rows += [(tr("Notiz"), note) for note in measurement.attached.notes]
    rows += [(tr("Anhang"), name) for name in measurement.attached.documents]
    return Fields(rows)


def _numbered_notes(group: list[ReportMeasurement]) -> list[Node]:
    """A table has no room for text, so notes and attachments follow it by row number."""
    lines = []
    for number, measurement in enumerate(group, 1):
        texts = [*measurement.attached.notes,
                 *(f"{tr('Anhang')} {d}" for d in measurement.attached.documents)]
        if measurement.data.comment:
            texts.insert(0, measurement.data.comment)
        lines += [f"{tr('Nr.')} {number}: {text}" for text in texts]
    return [Paragraph(line) for line in lines]


def place_nodes(places: list) -> list[Node]:
    rows = [(tr(p.name), note) for p in places for note in p.attached.notes]
    rows += [(tr(p.name), f"{tr('Anhang')} {name}") for p in places for name in p.attached.documents]
    images = [(path, tr(p.name)) for p in places for path in p.attached.images]
    return ([Fields(rows)] if rows else []) + ([Photos(images)] if images else [])


def _columns(group: list[ReportMeasurement]) -> list[tuple[str, str]]:
    columns: dict[str, str] = {}
    for measurement in group:
        for result in measurement.data.results:
            columns.setdefault(result.key, tr(result.label))
    return list(columns.items())


def _many(group: list[ReportMeasurement], options: dict) -> list[Node]:
    columns = _columns(group)
    details = _details(group)
    headers = [tr("Nr."), tr("Zeitpunkt"), *(tr(d) for d in details),
               *(label for _, label in columns), tr("Bewertung")]
    rows = []
    for number, measurement in enumerate(group, 1):
        cells = [str(number), measurement.local_time.strftime("%H:%M:%S") + _marks(measurement)]
        cells += [texts[number - 1] or "–" for texts in details.values()]
        for key, _ in columns:
            result = measurement.data.result(key)
            cells.append(_word(result.quantity.raw) if result else "–")
        cells.append(tr(VERDICT_TEXT[measurement.data.verdict]))
        rows.append(cells)
    # L1-PE and L1-L2 are different quantities, so their extremes say nothing.
    comparable = len(set(details.get("Leiter", ()))) <= 1
    wanted = options.get("summary", True) and comparable
    summary = _summary(group, columns, len(details)) if wanted else []
    return [Table(headers, rows, summary), *_numbered_notes(group)]


def _details(group: list[ReportMeasurement]) -> dict[str, list[str]]:
    """Where each row was measured, as far as the rows differ in that."""
    details = {}
    places = [m.data.location[-1] if m.data.location else "" for m in group]
    if len(set(places)) > 1:
        details["Messort"] = places
    conductors = [conductor_of(m.data.parameters) for m in group]
    if any(conductors):
        details["Leiter"] = conductors
    return details


def _summary(
    group: list[ReportMeasurement], columns: list[tuple[str, str]], details: int = 0
) -> list[list[str]]:
    """Min and max rows. Shows the instrument's own text, so nothing is reformatted."""
    lines = []
    for label, pick in (("Min", min), ("Max", max)):
        cells = [tr(label), "", *[""] * details]
        for key, _ in columns:
            found = [m.data.result(key) for m in group]
            numeric = [r for r in found if r and r.quantity.base_value is not None]
            cells.append(
                _word(pick(numeric, key=lambda r: r.quantity.base_value).quantity.raw)
                if numeric else "–"
            )
        lines.append([*cells, ""])
    return lines
