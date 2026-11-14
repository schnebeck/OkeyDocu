# OkeyDocu - okeydocu/campaign/line_conductors.py
# Which conductors reach a test point, and which readings are therefore not applicable.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""An element states how many line conductors reach it and whether N does; what it leaves open
it takes from the nearest element above that states it, like the RCD a circuit hangs on. The
instrument's AUTO runs measure every pair of conductors, whether they are there or not. A
reading between conductors the test point lacks is not applicable: it stays stored as it
came, it is only left out of the verdict and the report. The mark is worked out whenever it is
needed, so it follows the element when its statement changes."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from ..l10n.catalog import source_of
from ..model import Parameter, Verdict, conductor_of

LINE_CONDUCTORS, N_CONDUCTOR = "line_conductors", "n_conductor"
PRESENT, ABSENT = "with N", "without N"
SECOND_AND_THIRD = {"L2", "L3"}


@dataclass(frozen=True)
class Conductors:
    lines: int | None = None  # 1 or 3; None where no element states it
    neutral: bool | None = None  # None where no element states it

    def lacks(self, path: str) -> bool:
        """Whether a reading between the conductors of `path`, such as L2-PE, needs one that
        is not there."""
        parts = set(re.split(r"[-+]", path))
        if self.lines == 1 and parts & SECOND_AND_THIRD:
            return True
        return self.neutral is False and "N" in parts


def _lines(value: str) -> int | None:
    return int(value) if value in ("1", "3") else None


def neutral_of(value: str) -> bool | None:
    """A statement about N as a list holds it or in any catalogued language."""
    word = source_of(value) or value
    return None if not value else word != ABSENT


class ConductorBook:
    """What reaches each element, looked up once per element."""

    def __init__(self, db):
        self.db = db
        self._known: dict[int | None, Conductors] = {}

    def at(self, asset_id: int | None) -> Conductors:
        if asset_id in self._known:
            return self._known[asset_id]
        lines = neutral = None
        current, seen = asset_id, set()
        while current is not None and current not in seen and (lines is None or neutral is None):
            seen.add(current)
            row = self.db.asset(current)
            if row is None:
                break
            features = json.loads(row["features_json"] or "{}")
            noted = str(features.get(LINE_CONDUCTORS) or "").strip()
            lines = lines if lines is not None else _lines(noted)
            stated = str(features.get(N_CONDUCTOR) or "").strip()
            neutral = neutral if neutral is not None else neutral_of(stated)
            current = row["parent_id"]
        self._known[asset_id] = Conductors(lines, neutral)
        return self._known[asset_id]

    def omitted(self, row) -> bool:
        """Whether a stored measurement is not applicable at the element it was booked on."""
        stored = json.loads(row["parameters_json"] or "[]")
        path = conductor_of([Parameter(item["key"], item["value"]) for item in stored])
        return bool(path) and self.at(row["asset_id"]).lacks(path)

    def omitted_ids(self, rows) -> set[int]:
        return {row["id"] for row in rows if self.omitted(row)}


def failed_counts(db, campaign_id: int | None = None) -> dict[int, int]:
    """Failed measurements by campaign, the not applicable ones left out."""
    query = ("SELECT id, campaign_id, asset_id, parameters_json FROM measurements"
             " WHERE verdict = ?")
    rows = db.query(query, Verdict.FAILED.value) if campaign_id is None else \
        db.query(query + " AND campaign_id = ?", Verdict.FAILED.value, campaign_id)
    book, counts = ConductorBook(db), {}
    for row in rows:
        if not book.omitted(row):
            counts[row["campaign_id"]] = counts.get(row["campaign_id"], 0) + 1
    return counts
