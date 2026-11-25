# OkeyDocu - okeydocu/campaign/upstream_rcd.py
# The RCD in front of an installation: stated by the installation, not an element of it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A machine is often protected by an RCD of the building installation. That RCD is no part
of the machine and gets no element in its structure: the machine states it instead, as the
RCD in front of it, at the nearest element at or above the measured one whose kind can state
it. A measurement that needs the data of an RCD and finds no RCD element takes them from
there; it is then taken at the supply of that element and booked on the element measured."""

from __future__ import annotations

import json

from ..devices.guide import IN_FRONT, RCD_PLACE

# What a guide asks of an RCD, by the feature that states it for the RCD in front.
UPSTREAM = {"rcd_type": "upstream_rcd_type",
            "rated_residual_current": "upstream_residual_current",
            "rated_current": "upstream_rated_current"}
OWNER = "rcd_type"  # the feature that marks an RCD element
__all__ = ["IN_FRONT", "OWNER", "RCD_PLACE", "UPSTREAM", "holder", "stated_in_front",
           "units_in_front"]


def holder(db, asset_id: int | None) -> int | None:
    """The nearest element at or above `asset_id` whose kind can state an RCD in front."""
    kinds = {row["kind"] for row in db.query(
        "SELECT kind FROM kind_features WHERE key=?", UPSTREAM[OWNER])}
    seen = set()
    while asset_id is not None and asset_id not in seen:
        seen.add(asset_id)
        row = db.asset(asset_id)
        if row is None:
            return None
        if row["kind"] in kinds:
            return asset_id
        asset_id = row["parent_id"]
    return None


def stated_in_front(db, asset_id: int | None) -> dict[str, str]:
    """What the holder at or above `asset_id` states of the RCD in front, by its own keys."""
    found = holder(db, asset_id)
    if found is None:
        return {}
    features = json.loads(db.asset(found)["features_json"] or "{}")
    stated = {key: str(features.get(key) or "").strip() for key in UPSTREAM.values()}
    return {key: value for key, value in stated.items() if value}


def units_in_front(db, holder_id: int) -> dict[str, str]:
    kind = db.asset(holder_id)["kind"]
    rows = db.query("SELECT key, unit FROM kind_features WHERE kind=?", kind)
    return {row["key"]: row["unit"] for row in rows if row["key"] in UPSTREAM.values()}
