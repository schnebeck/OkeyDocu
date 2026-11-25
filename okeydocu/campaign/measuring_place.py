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
from .upstream_rcd import IN_FRONT, OWNER, RCD_PLACE, UPSTREAM, holder, stated_in_front, \
    units_in_front
from .line_conductors import ABSENT, LINE_CONDUCTORS, N_CONDUCTOR, PRESENT, ConductorBook, \
    neutral_of

SUPPLY_CONNECTION = "supply_connection"  # fixed, or the plug the element is supplied through


@dataclass(frozen=True)
class MeasuringPlace:
    asset_id: int | None
    title: str = ""
    path: tuple[str, ...] = ()  # names from the installation down to the element's parent
    features: dict[str, str] = field(default_factory=dict)
    units: dict[str, str] = field(default_factory=dict)
    kind: str = ""
    inherited: dict[str, str] = field(default_factory=dict)  # stated above, not at the element
    holder_id: int | None = None  # the element that states the RCD in front, where one is meant

    @property
    def is_new(self) -> bool:
        return self.asset_id is None and bool(self.kind)

    def entered(self, features: dict[str, str], title: str = "") -> "MeasuringPlace":
        """The place as it reads with what has been entered so far."""
        return replace(self, features={**self.features, **features},
                       title=title or self.title)

    @property
    def in_front(self) -> bool:
        """Whether the RCD of this measurement stands in front of the installation."""
        return self.holder_id is not None

    def stated(self, key: str) -> str:
        """What the element states for `key`; of an RCD, where that one stands in front, what
        is stated of it."""
        if self.in_front:
            if key == RCD_PLACE:
                return IN_FRONT
            key = UPSTREAM.get(key, key)
        value = str(self.features.get(key) or self.inherited.get(key) or "").strip()
        unit = self.units.get(key, "")
        return f"{value} {unit}".strip() if value else ""

    def missing(self, keys) -> list[str]:
        return [key for key in keys if not self.stated(key)]

    @property
    def poles(self) -> int:
        """Two for one line conductor, four for three, as stated or by the poles."""
        lines = self.stated(LINE_CONDUCTORS)
        if lines in ("1", "3"):
            return 2 if lines == "1" else 4
        return 4 if str(self.features.get("number_of_poles") or "") in ("3", "4") else 2

    @property
    def has_n(self) -> bool | None:
        """Whether N reaches the test point; None where nothing says."""
        return neutral_of(self.stated(N_CONDUCTOR))

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
                                             self.stated("rcd_type")) if text)
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


def _from_above(db, parent_id: int | None) -> dict[str, str]:
    """The conductors and the supply connection elements above state, in the words their
    lists hold."""
    known = ConductorBook(db).at(parent_id)
    found = {}
    if known.lines is not None:
        found[LINE_CONDUCTORS] = str(known.lines)
    if known.neutral is not None:
        found[N_CONDUCTOR] = PRESENT if known.neutral else ABSENT
    connection = _nearest_above(db, parent_id, SUPPLY_CONNECTION)
    if connection:
        found[SUPPLY_CONNECTION] = connection
    return found


def _nearest_above(db, asset_id: int | None, key: str) -> str:
    """What the nearest element at or above `asset_id` states for `key`."""
    seen = set()
    while asset_id is not None and asset_id not in seen:
        seen.add(asset_id)
        value = str(db.asset_features(asset_id).get(key) or "").strip()
        if value:
            return value
        row = db.asset(asset_id)
        asset_id = row["parent_id"] if row is not None else None
    return ""


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
    if found is not None:
        return _place_at(db, found, root_id)
    if guide.owner_feature == OWNER and stated_in_front(db, asset_id):
        return in_front_place(service, asset_id, root_id)
    return MeasuringPlace(None)


def _place_at(db, found: int, root_id: int) -> MeasuringPlace:
    row = db.asset(found)
    title = " ".join(part for part in (row["identifier"], row["name"]) if part)
    path = _path(db, row["parent_id"], root_id) if found != root_id else ()
    units = {r["key"]: r["unit"] for r in db.query(
        "SELECT key, unit FROM kind_features WHERE kind=?", row["kind"])}
    return MeasuringPlace(found, title, path, json.loads(row["features_json"] or "{}"), units,
                          row["kind"], _from_above(db, row["parent_id"]))


def in_front_place(service, asset_id: int, root_id: int) -> MeasuringPlace | None:
    """`asset_id` as the place of a measurement that needs an RCD, with the RCD in front as
    the nearest element that can state it does; None where no element at or above can."""
    db = service.db
    found = holder(db, asset_id)
    if found is None:
        return None
    place = _place_at(db, asset_id, root_id)
    held = json.loads(db.asset(found)["features_json"] or "{}")
    in_front = {key: str(held.get(key) or "") for key in UPSTREAM.values()}
    return replace(place, features={**place.features, **in_front},
                   units={**place.units, **units_in_front(db, found)}, holder_id=found)


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
    return MeasuringPlace(None, "", _path(db, parent_id, root_id), {}, units, kind,
                          _from_above(db, parent_id))


def make_place(service, place: MeasuringPlace, parent_id: int, name: str,
               identifier: str) -> int:
    """Makes the element entered on the way; its id."""
    db = service.db
    parent = db.asset(parent_id)
    asset_id = db.add_asset(parent["customer_id"], place.kind, name, parent_id,
                            identifier=identifier)
    db.set_asset_features(asset_id, {k: str(v) for k, v in place.features.items()})
    return asset_id


def measured_functions(db, campaign_id: int) -> set[str]:
    """The functions a campaign has readings of."""
    rows = db.query("SELECT DISTINCT function FROM measurements WHERE campaign_id=?",
                    campaign_id)
    return {row["function"] for row in rows}
