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

from ..l10n import N_, tr
from .language import UNIT_SPACE

# Narrow spaces around the slash: kept before it, a line may break after it.
PATH = "\u202f/\u2009"

if TYPE_CHECKING:
    from .context import ReportMeasurement


def asset_features(db, asset) -> list[tuple[str, str]]:
    """The features noted on the element, in the order of its kind; empty ones stay out."""
    kind, values = db.kind(asset["kind"]), db.asset_features(asset["id"])
    return [(feature.label, f"{values[feature.key]}{UNIT_SPACE}{feature.unit}".strip())
            for feature in (kind.features if kind else ()) if values.get(feature.key)]


IDENTIFIER, MANUFACTURER, TYPE, REMARK = (N_("Identifier"), N_("Manufacturer"), N_("Type"),
                                           N_("Remark"))
BASIS = N_("Test basis")


def asset_card(db, asset) -> list[tuple[str, str]]:
    """What the element is, as a test object: its identifier, maker and type, a test basis of
    its own, the features noted on it and its remark, which may say how it was measured.
    Empty ones stay out."""
    known = [(tr(IDENTIFIER), asset["identifier"]), (tr(MANUFACTURER), asset["manufacturer"]),
             (tr(TYPE), asset["type"])]
    # Only a test basis of its own, other than the one above, is news below the title.
    above = db.test_basis(asset["parent_id"])[1] if asset["parent_id"] is not None else None
    if above is not None and asset["basis"] and asset["basis"] != above:
        known.append((tr(BASIS), asset["basis"]))
    rows = [(label, value) for label, value in known if value]
    return rows + asset_features(db, asset) + ([(tr(REMARK), asset["comment"])]
                                               if asset["comment"] else [])


@dataclass
class Level:
    asset_id: int | None
    title: str
    kind: str = ""
    card: list[tuple[str, str]] = field(default_factory=list)
    measurements: list[ReportMeasurement] = field(default_factory=list)
    remark: str = ""


def structure_levels(service, root_id: int, measured: list[ReportMeasurement]) -> list[Level]:
    """The installation first, then each element below it; elements side by side in the
    order they were first measured, so the report follows the way the inspection went."""
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
    first: dict[int, object] = {}

    def earliest(row):
        """The first time anything was measured on the element or below it."""
        times = [m.local_time for m in by_place.get(row["id"], ())]
        times += [t for t in map(earliest, below.get(row["id"], ())) if t is not None]
        first[row["id"]] = min(times) if times else None
        return first[row["id"]]

    def visit(row, names: list[str]) -> None:
        mine = by_place.pop(row["id"], [])
        if mine:
            levels.append(Level(row["id"], PATH.join(names) or row["name"],
                                kinds.get(row["kind"], ""), asset_card(db, row),
                                sorted(mine, key=lambda m: m.local_time), row["comment"]))
        # Elements side by side follow in the order they were measured in.
        children = sorted(below.get(row["id"], ()),
                          key=lambda child: (first[child["id"]] is None,
                                             first[child["id"]] or 0, child["name"]))
        for child in children:
            visit(child, [*names, child["name"]])

    earliest(root)
    visit(root, [])
    # An element moved to another customer's tree still shows what was measured on it.
    for place, mine in by_place.items():
        asset = db.asset(place)
        levels.append(Level(place, asset["name"] if asset else "–", measurements=mine))
    return levels
