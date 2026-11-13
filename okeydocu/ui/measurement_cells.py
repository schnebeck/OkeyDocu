# OkeyDocu - okeydocu/ui/measurement_cells.py
# What the cells of the measurement table say, and how they sort.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..campaign.service import LOCATION_SEPARATOR
from ..l10n import N_, tr
from ..model import conductor_of
from .common import stored_parameters
from .readings import readings_line, stored_values

RECORD, UNIT = "\x1e", "\x1f"  # the separators the search query joins checklist values with

CUSTOMER, ASSET, CAMPAIGN = 1, 2, 3
PLACE, VALUES, VERDICT = 4, 6, 8
CAPTURE = 9
SHARED_COLUMNS = {
    CUSTOMER: N_("Customer"), ASSET: N_("Installation"), CAMPAIGN: N_("Campaign"),
    PLACE: N_("Measuring location"), 5: N_("Designation"), 7: N_("Photos"),
    VERDICT: N_("Verdict"), CAPTURE: N_("Capture"),
}


def values_text(row) -> str:
    """Only some functions have a conductor, so it stands with the reading it belongs to.

    A checklist says its answers first: they are what the row is about, the question
    only says which one.
    """
    figures = readings_line(row["function"], row["verdict"], stored_values(row["value_parts"]))
    values = _checks(row["checks"]) or figures or row["value_text"] or ""
    conductor = conductor_of(stored_parameters(row))
    return f"{conductor}:  {values}" if conductor else values


def path_of(row) -> list[str]:
    """Where in the installation, without repeating the installation itself."""
    parts = row["location"].split(LOCATION_SEPARATOR) if row["location"] else []
    return parts[1:] if parts[:1] == [row["asset_name"]] else parts


def sort_key(column: int, row):
    """Time and photos sort as what they are; values by function first, then by size."""
    if column == 0:
        return (row["local_time"], row["id"])
    if column == 7:
        return row["photo_count"] or 0
    if column == VALUES:
        first = row["first_value"]
        return (row["function"] or "", float("inf") if first is None else first)
    return None


def shared_start(paths: list[list[str]]) -> list[str]:
    """What all paths begin with. The last part of each stays, it names the place."""
    shared = []
    for parts in zip(*(path[:-1] for path in paths)):
        if len(set(parts)) > 1:
            break
        shared.append(parts[0])
    return shared




def _checks(text: str | None) -> str:
    """`key` US `text` pairs, RS between them, in the order they were recorded."""
    if not text:
        return ""
    lines, question = [], ""
    for entry in text.split(RECORD):
        key, _, value = entry.partition(UNIT)
        if key == "question":
            question = value
        elif key == "answer":
            lines.append(f"{value} – {question}" if question else value)
            question = ""
        else:
            lines.append(tr("Remark: {value}", value=value))
    return "   ".join(lines)
