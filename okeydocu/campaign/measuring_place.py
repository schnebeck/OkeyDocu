# OkeyDocu - okeydocu/campaign/measuring_place.py
# The element a guided measurement is taken at, with what its guide needs it to state.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A guide that names an owner feature, such as an RCD type, is taken at the nearest element
at or above the chosen place whose kind has that feature; any other guide at the place itself.
What the element does not state is missing, never guessed: the drawing then shows the usual
layout and says so. Where no such element exists yet, the place is one still to be made: its
kind and where it will hang are known, everything else is entered on the way."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace

from ..devices.guide import Guide
from ..l10n.catalog import source_of


@dataclass(frozen=True)
class MeasuringPlace:
    asset_id: int | None
    title: str = ""
    path: tuple[str, ...] = ()  # names from the installation down to the element's parent
    features: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    kind: str = ""

    @property
    def is_new(self) -> bool:
        return self.asset_id is None and bool(self.kind)

    def entered(self, features: dict[str, str], title: str = "") -> "MeasuringPlace":
        """The place as it reads with what has been entered so far."""
        return replace(self, features={**self.features, **features},
                       title=title or self.title)

    def stated(self, key: str) -> str:
        value = str(self.features.get(key) or "").strip()
        unit = self.units.get(key, "")
        return f"{value} {unit}".strip() if value else ""

    def missing(self, keys) -> list[str]:
        return [key for key in keys if not self.stated(key)]

    @property
    def poles(self) -> int:
        return 4 if str(self.features.get("number_of_poles") or "") in ("3", "4") else 2

    @property
    def n_left(self) -> bool:
        noted = str(self.features.get("n_terminal") or "").strip()
        return "left" in (noted, source_of(noted))

    def lines(self, keys: tuple[str, ...] = ()) -> list[str]:
        """What the drawing prints: the features named by `keys` that are stated, or for an
        RCD rated residual current and type, rated current."""
        if keys:
            return [self.stated(key) for key in keys if self.stated(key)]
        first = " · ".join(text for text in (self.stated("rated_residual_current"),
                                             str(self.features.get("rcd_type") or "")) if text)
        return [first or "? mA", self.stated("rated_current") or "? A"]


def _kinds_with(db, feature: str) -> set[str]:
    rows = db.query("SELECT kind FROM kind_features WHERE key=?", feature)
    return {row["kind"] for row in rows}


def _measured_at(db, guide: Guide, asset_id: int | None) -> int | None:
    if not guide.owner_feature:
        return asset_id
    kinds, seen = _kinds_with(db, guide.owner_feature), set()
    while asset_id is not None and asset_id not in seen:
        seen.add(asset_id)
        row = db.asset(asset_id)
        if row is None:
            return None
        if row["kind"] in kinds:
            return asset_id
        asset_id = row["parent_id"]
    return None


def _title(row) -> str:
    return " ".join(part for part in (row["name"], row["identifier"]) if part)


def _path(db, asset_id: int | None, root_id: int) -> tuple[str, ...]:
    """Name and identifier of every element from the installation down to `asset_id`."""
    names, seen = [], set()
    while asset_id is not None and asset_id not in seen:
        seen.add(asset_id)
        row = db.asset(asset_id)
        names.insert(0, _title(row))
        asset_id = None if asset_id == root_id else row["parent_id"]
    return tuple(names)


def measuring_place(service, guide: Guide, asset_id: int | None,
                    root_id: int) -> MeasuringPlace:
    """Where the guide sends the probes when readings go to `asset_id`."""
    db = service.db
    found = _measured_at(db, guide, asset_id)
    if found is None:
        return MeasuringPlace(None)
    row = db.asset(found)
    title = " ".join(part for part in (row["identifier"], row["name"]) if part)
    path = _path(db, row["parent_id"], root_id) if found != root_id else ()
    units = {r["key"]: r["unit"] for r in db.query(
        "SELECT key, unit FROM kind_features WHERE kind=?", row["kind"])}
    return MeasuringPlace(found, title, path, json.loads(row["features_json"] or "{}"), units,
                          row["kind"])


def _owner_kind(db, guide: Guide) -> str:
    rows = db.query("SELECT f.kind FROM kind_features f JOIN asset_kinds k ON k.key = f.kind"
                    " WHERE f.key=? ORDER BY k.position", guide.owner_feature)
    return rows[0]["kind"] if rows else ""


def new_place(service, guide: Guide, parent_id: int, root_id: int) -> MeasuringPlace:
    """An element still to be made below `parent_id`, of the kind the guide is taken at."""
    db = service.db
    kind = _owner_kind(db, guide) if guide.owner_feature else ""
    units = {r["key"]: r["unit"] for r in db.query(
        "SELECT key, unit FROM kind_features WHERE kind=?", kind)}
    return MeasuringPlace(None, "", _path(db, parent_id, root_id), {}, units, kind)


def make_place(service, place: MeasuringPlace, parent_id: int, name: str,
               identifier: str) -> int:
    """Makes the element entered on the way; its id."""
    db = service.db
    parent = db.asset(parent_id)
    asset_id = db.add_asset(parent["customer_id"], place.kind, name, parent_id,
                            identifier=identifier)
    db.set_asset_features(asset_id, {k: str(v) for k, v in place.features.items()})
    return asset_id


def candidates(service, guide: Guide, root_id: int) -> list[tuple[int, str]]:
    """The elements of an installation a guide can be taken at, as (id, title)."""
    db = service.db
    kinds = _kinds_with(db, guide.owner_feature) if guide.owner_feature else None
    found = []
    for asset_id in service.subtree(root_id):
        row = db.asset(asset_id)
        if kinds is None or row["kind"] in kinds:
            found.append((asset_id, " ".join(p for p in (row["identifier"], row["name"]) if p)))
    return found


def places(service, root_id: int) -> list[tuple[int, str]]:
    """Every element of an installation with its path, for hanging a new one below it."""
    db = service.db
    return [(asset_id, " › ".join(_path(db, asset_id, root_id)))
            for asset_id in service.subtree(root_id)]
