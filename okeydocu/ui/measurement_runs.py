# OkeyDocu - okeydocu/ui/measurement_runs.py
# The lines of the measurement table: single measurements, and runs folded into one line.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTableWidget

from ..campaign.service import LOCATION_SEPARATOR
from ..l10n import plural, tr
from ..model import Parameter, Verdict, conductor_of
from ..reporting.context import VERDICT_TEXT
from .common import MEMBERS, POINT_ID, ROW_ID, RUN_ID, function_short
from .measurement_cells import PLACE, VALUES, VERDICT, sort_key, values_text
from .measurement_detail import capture_text
from .setting_warning import mark_row
from .table_columns import GROUP, HEAD, ORDER, SortItem
from .verdict_marks import verdict_icon

STEP_INDENT = "   "
POINT_GREY = "#8a8f94"


@dataclass
class Line:
    texts: list[str]
    keys: list  # per column; None sorts by the text
    verdict: str
    row_id: int | None = None  # the measurement; a run's head stands for several
    run_id: int | None = None  # on the head of a run and on each of its steps
    members: list[int] = field(default_factory=list)
    order: int = 0  # 0 for the head, then the steps as they were taken
    head: list | None = None  # a step sorts among other lines as its head does
    opened: bool = False
    point: int | None = None  # a point of a repeat inspection still to be taken
    warning: str = ""  # settings that differ from the element, for this line or its steps


def _place(path: list[str], area: list[str]) -> str:
    return LOCATION_SEPARATOR.join(path[len(area):])


def _measurement(row, when: datetime, show_time: Callable[[datetime], str], place: str) -> Line:
    texts = [
        show_time(when), row["customer_name"], row["asset_name"],
        row["campaign_title"], place, function_short(row["function"]), values_text(row),
        str(row["photo_count"] or ""), tr(VERDICT_TEXT[Verdict(row["verdict"])]), capture_text(row),
    ]
    return Line(texts, [sort_key(column, row) for column in range(len(texts))], row["verdict"],
                row["id"])


def _verdict(rows) -> str:
    verdicts = {row["verdict"] for row in rows}
    if Verdict.FAILED.value in verdicts:
        return Verdict.FAILED.value
    if verdicts == {Verdict.PASSED.value}:
        return Verdict.PASSED.value
    return Verdict.NOT_EVALUATED.value


def _head(run_id: int, steps: list[Line], rows: list, opened: bool) -> Line:
    """What the run's steps share, and how many there are, with the defects among them."""
    first = rows[0]
    line = Line(list(steps[0].texts), list(steps[0].keys), _verdict(rows), None, run_id,
                [row["id"] for row in rows], opened=opened)
    places = {step.texts[PLACE] for step in steps}
    failed = sum(row["verdict"] == Verdict.FAILED.value for row in rows)
    summary = f"{first['run_name']}  ·  " + plural(len(rows), "{count} step", "{count} steps")
    if failed:
        summary += "  ·  " + plural(failed, "{count} defect", "{count} defects")
    photos = sum(row["photo_count"] or 0 for row in rows)
    line.texts[PLACE] = places.pop() if len(places) == 1 else tr("several locations")
    line.texts[5] = first["run_kind"] or line.texts[5]
    line.texts[VALUES] = summary
    line.texts[7] = str(photos or "")
    line.texts[VERDICT] = tr(VERDICT_TEXT[Verdict(line.verdict)])
    line.keys[7], line.keys[VALUES] = photos, (line.texts[5], float("inf"))
    return line


def table_lines(rows, opened: set[int], show_time: Callable[[datetime], str], area: list[str],
                paths, warnings: dict[int, str] | None = None) -> list[Line]:
    """Rows as the search gave them; each run becomes a head, its steps follow if opened.

    `show_time` writes the time of a row; `warnings` says, by measurement, which settings
    differ from the element. A run's head carries the first of its steps'.
    """
    lines: list[Line | int] = []  # a run's number keeps the place of its head
    runs: dict[int, list[tuple[Line, object]]] = {}
    for row, path in zip(rows, paths):
        line = _measurement(row, datetime.fromisoformat(row["local_time"]), show_time,
                            _place(path, area))
        line.warning = (warnings or {}).get(row["id"], "")
        run_id = row["run_id"]
        if run_id is None:
            lines.append(line)
            continue
        if run_id not in runs:
            runs[run_id] = []
            lines.append(run_id)
        runs[run_id].append((line, row))
    result = []
    for line in lines:
        if isinstance(line, Line):
            result.append(line)
            continue
        steps = [step for step, _ in runs[line]]
        members = [row for _, row in runs[line]]
        head = _head(line, steps, members, line in opened)
        head.warning = next((step.warning for step in steps if step.warning), "")
        result.append(head)
        if head.opened:
            keys = [key if key is not None else text.casefold()
                    for key, text in zip(head.keys, head.texts)]
            for order, (step, row) in enumerate(runs[line], start=1):
                step.run_id, step.order, step.head = line, order, keys
                step.texts[0] = STEP_INDENT + step.texts[0]
                step.texts[5] = row["step_name"] or step.texts[5]
                result.append(step)
    return result


def point_line(row, step, place: str) -> Line:
    """A point of a repeat inspection not taken yet: what to take, in grey.

    The conductor leads as it does for a measurement, it tells points of one kind apart.
    """
    skipped = row["status"] == "skipped"
    parameters = [Parameter(key, value) for key, value in step.parameters]
    conductor = conductor_of(parameters)
    parts = [tr("skipped: {note}", note=row["note"]) if skipped else tr("missing")]
    if step.kind == "check" and step.question and step.question != step.title:
        parts[0] += f" – {step.question}"
    parts += [p.value for p in parameters if p.value != conductor]
    parts += [tr("Limit {limits}", limits=" ".join(x for x in (low, up) if x))
              for _, _, low, up in step.limits]
    detail = "  ·  ".join(parts)
    state = tr("skipped") if skipped else tr("open", context="state")
    texts = [state, "", "", "", place, step.title,
             f"{conductor}:  {detail}" if conductor else detail, "", "", ""]
    keys = [("~", row["position"]), None, None, None, None, None, None, None, None, None]
    line = Line(texts, keys, Verdict.NOT_EVALUATED.value)
    line.point = row["id"]
    return line


def write_line(table: QTableWidget, index: int, line: Line) -> None:
    for column, text in enumerate(line.texts):
        item = SortItem(text, line.keys[column])
        if line.run_id is not None:
            item.setData(GROUP, line.run_id)
            item.setData(ORDER, line.order)
            if line.head is not None:
                item.setData(HEAD, line.head[column])
        table.setItem(index, column, item)
    if line.verdict == Verdict.FAILED.value:
        cell = table.item(index, VERDICT)
        cell.setForeground(QColor("#c0392b"))
        font = cell.font()
        font.setBold(True)
        cell.setFont(font)
    if line.warning:
        mark_row(table, index, line.warning)
    first = table.item(index, 0)
    if line.point is not None:
        first.setData(POINT_ID, line.point)
        for column in range(len(line.texts)):
            table.item(index, column).setForeground(QColor(POINT_GREY))
    first.setData(ROW_ID, line.row_id)
    head = line.row_id is None and line.run_id is not None
    first.setIcon(verdict_icon(line.verdict, line.opened if head else None))
    if line.row_id is None and line.run_id is not None:
        first.setData(RUN_ID, line.run_id)
        first.setData(MEMBERS, line.members)
        first.setToolTip(tr("Click on the time or double-click to fold the steps open and shut"))
