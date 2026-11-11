# EasyMeasurement - easymeasurement/reporting/levels.py
# The elements of the installation that have measurements, in the order of the structure tree.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .language import UNIT_SPACE

if TYPE_CHECKING:
    from .context import ReportMeasurement


def asset_features(db, asset) -> list[tuple[str, str]]:
    """The features noted on the element, in the order of its kind; empty ones stay out."""
    kind, values = db.kind(asset["kind"]), db.asset_features(asset["id"])
    return [(feature.label, f"{values[feature.key]}{UNIT_SPACE}{feature.unit}".strip())
            for feature in (kind.features if kind else ()) if values.get(feature.key)]


@dataclass
class Level:
    asset_id: int | None
    title: str
    kind: str = ""
    features: list[tuple[str, str]] = field(default_factory=list)
    measurements: list[ReportMeasurement] = field(default_factory=list)


def structure_levels(service, root_id: int, measured: list[ReportMeasurement]) -> list[Level]:
    db = service.db
    root = db.asset(root_id)
    below: dict[int | None, list] = {}
    for row in db.assets(root["customer_id"]):
        below.setdefault(row["parent_id"], []).append(row)
    by_place: dict[int, list[ReportMeasurement]] = {}
    for measurement in measured:
        place = measurement.place_id if measurement.place_id is not None else root_id
        by_place.setdefault(place, []).append(measurement)
    kinds = db.kind_labels()
    levels: list[Level] = []

    def visit(row, names: list[str]) -> None:
        mine = by_place.pop(row["id"], [])
        if mine:
            levels.append(Level(row["id"], " / ".join(names) or row["name"],
                                kinds.get(row["kind"], ""), asset_features(db, row),
                                sorted(mine, key=lambda m: m.local_time)))
        for child in below.get(row["id"], ()):
            visit(child, [*names, child["name"]])

    visit(root, [])
    # An element moved to another customer's tree still shows what was measured on it.
    for place, mine in by_place.items():
        asset = db.asset(place)
        levels.append(Level(place, asset["name"] if asset else "–", measurements=mine))
    return levels
