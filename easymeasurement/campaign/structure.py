# EasyMeasurement - easymeasurement/campaign/structure.py
# Rebuilding an installation's structure and booking measurements onto its elements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..store import CampaignClosed
from .records import LOCATION_SEPARATOR

_BELOW = (
    "WITH RECURSIVE below(id) AS (SELECT ? UNION ALL"
    " SELECT a.id FROM assets a JOIN below b ON a.parent_id = b.id)"
)
DEFAULT_KIND = "measuring_point"


class StructureError(ValueError):
    """The structure cannot change like this; the text says why."""


class StructureMixin:
    """A sealed record keeps its places: what it refers to may move, but not go."""

    def subtree(self, asset_id: int) -> list[int]:
        return [row["id"] for row in self.db.query(_BELOW + " SELECT id FROM below", asset_id)]

    def place_path(self, asset_id: int, root_id: int | None = None) -> str:
        """Names from `root_id` (or the top) down to the element, as a measurement's place."""
        names = []
        while asset_id is not None:
            asset = self.db.asset(asset_id)
            names.insert(0, asset["name"])
            asset_id = None if asset_id == root_id else asset["parent_id"]
        return LOCATION_SEPARATOR.join(names)

    def place_counts(self, campaign_id: int) -> dict[int | None, int]:
        rows = self.db.query(
            "SELECT asset_id, count(*) AS n FROM measurements WHERE campaign_id=?"
            " GROUP BY asset_id", campaign_id,
        )
        return {row["asset_id"]: row["n"] for row in rows}

    def previous_counts(self, campaign_id: int) -> dict[int | None, int]:
        """What the last closed campaign on the same installation measured where."""
        campaign = self.campaign(campaign_id)
        row = self.db.one(
            "SELECT id FROM campaigns WHERE asset_id=? AND status='closed' AND id<>?"
            " AND started_at <= ? ORDER BY started_at DESC, id DESC LIMIT 1",
            campaign["asset_id"], campaign_id, campaign["started_at"],
        )
        return self.place_counts(row["id"]) if row else {}

    # Measurements ----------------------------------------------------------

    def move_measurements(self, measurement_ids: list[int], asset_id: int) -> None:
        """The place text follows the element, so the report reads the new place."""
        rows = [self.db.one("SELECT * FROM measurements WHERE id=?", i) for i in measurement_ids]
        for row in rows:
            if self.campaign(row["campaign_id"])["status"] != "open":
                raise CampaignClosed("Messungen abgeschlossener Kampagnen bleiben, wo sie sind.")
        with self.db.transaction() as connection:
            for row in rows:
                root = self.campaign(row["campaign_id"])["asset_id"]
                connection.execute(
                    "UPDATE measurements SET asset_id=?, location=? WHERE id=?",
                    (asset_id, self.place_path(asset_id, root), row["id"]),
                )
        for campaign_id in {row["campaign_id"] for row in rows}:
            self.rematch(campaign_id)

    def _relocate(self, asset_id: int) -> None:
        """Open measurements below an element read its new name or place."""
        rows = self.db.query(
            _BELOW + " SELECT m.id, m.asset_id, c.asset_id AS root FROM measurements m"
            " JOIN campaigns c ON c.id = m.campaign_id"
            " WHERE c.status='open' AND m.asset_id IN (SELECT id FROM below)", asset_id,
        )
        with self.db.transaction() as connection:
            for row in rows:
                connection.execute(
                    "UPDATE measurements SET location=? WHERE id=?",
                    (self.place_path(row["asset_id"], row["root"]), row["id"]),
                )

    # Elements --------------------------------------------------------------

    def add_element(self, parent_id: int, kind: str, name: str) -> int:
        parent = self.db.asset(parent_id)
        return self.db.add_asset(parent["customer_id"], kind, name, parent_id=parent_id)

    def rename_element(self, asset_id: int, name: str) -> None:
        if not name.strip():
            raise StructureError("Ein Element braucht einen Namen.")
        self.db.execute("UPDATE assets SET name=? WHERE id=?", name.strip(), asset_id)
        self._relocate(asset_id)

    def move_element(self, asset_id: int, parent_id: int | None) -> None:
        """Anywhere within the same customer, never below itself."""
        asset = self.db.asset(asset_id)
        if parent_id is not None:
            if parent_id in self.subtree(asset_id):
                raise StructureError("Ein Element lässt sich nicht unter sich selbst schieben.")
            if self.db.asset(parent_id)["customer_id"] != asset["customer_id"]:
                raise StructureError("Elemente bleiben bei ihrem Kunden.")
        self.db.execute("UPDATE assets SET parent_id=? WHERE id=?", parent_id, asset_id)
        self._relocate(asset_id)

    def group_elements(self, asset_ids: list[int], kind: str, name: str) -> int:
        """A new element in place of the first one, with all of them below it."""
        first = self.db.asset(asset_ids[0])
        group = self.db.add_asset(first["customer_id"], kind, name, parent_id=first["parent_id"])
        for asset_id in asset_ids:
            self.move_element(asset_id, group)
        return group

    def deletion_blocker(self, asset_id: int) -> str:
        """Why the element cannot go, or an empty text."""
        below = _BELOW + " SELECT count(*) AS n FROM {} WHERE {} IN (SELECT id FROM below){}"
        if self.db.one(below.format("campaigns", "asset_id", ""), asset_id)["n"]:
            return "An diesem Element oder darunter hängt eine ganze Kampagne."
        sealed = " AND campaign_id IN (SELECT id FROM campaigns WHERE status='closed')"
        for table in ("measurements", "attachments"):
            if self.db.one(below.format(table, "asset_id", sealed), asset_id)["n"]:
                return "Abgeschlossene Kampagnen haben hier gemessen und brauchen den Ort."
        return ""

    def delete_element(self, asset_id: int) -> None:
        """What open campaigns booked here moves up to the parent, then the element goes."""
        blocker = self.deletion_blocker(asset_id)
        if blocker:
            raise StructureError(blocker)
        parent = self.db.asset(asset_id)["parent_id"]
        doomed = self.subtree(asset_id)
        moving = [
            row["id"] for row in self.db.query(
                _BELOW + " SELECT id FROM measurements WHERE asset_id IN (SELECT id FROM below)",
                asset_id,
            )
        ]
        if moving and parent is not None:
            self.move_measurements(moving, parent)
        marks = ",".join("?" * len(doomed))
        with self.db.transaction() as connection:
            connection.execute(
                f"UPDATE attachments SET asset_id=? WHERE asset_id IN ({marks})", (parent, *doomed)
            )
            for element in reversed(doomed):  # children first
                connection.execute("DELETE FROM assets WHERE id=?", (element,))

    def empty_elements(self, root_id: int | None, customer_id: int | None = None) -> list[int]:
        """The topmost elements below `root_id` with nothing recorded in their whole branch.

        Without a root, below every installation of `customer_id`, the tops included.
        """
        used = {
            row["asset_id"] for row in self.db.query(
                "SELECT asset_id FROM measurements WHERE asset_id IS NOT NULL UNION"
                " SELECT asset_id FROM attachments WHERE asset_id IS NOT NULL UNION"
                " SELECT asset_id FROM campaigns"
            )
        }
        if root_id is not None:
            customer_id = self.db.asset(root_id)["customer_id"]
        children: dict[int | None, list[int]] = {}
        for row in self.db.assets(customer_id):
            children.setdefault(row["parent_id"], []).append(row["id"])

        def empty(node: int) -> bool:
            return node not in used and all(empty(child) for child in children.get(node, ()))

        found: list[int] = []

        def collect(node: int) -> None:
            for child in children.get(node, ()):
                if empty(child):
                    found.append(child)
                else:
                    collect(child)

        collect(root_id)
        return found

    def place_for_path(self, root_id: int, path: tuple[str, ...]) -> int:
        """The element a device path names below `root_id`; missing ones are created.

        The path starts wherever the instrument's tree starts, so it is read from the
        last part that names the root itself, if any.
        """
        names = [name.strip() for name in path if name.strip()]
        root_name = self.db.asset(root_id)["name"].casefold()
        hits = [i for i, name in enumerate(names) if name.casefold() == root_name]
        if hits:
            names = names[hits[-1] + 1:]
        current = root_id
        for name in names:
            row = self.db.one("SELECT id FROM assets WHERE parent_id=? AND name=? COLLATE NOCASE",
                              current, name)
            current = row["id"] if row else self.add_element(current, DEFAULT_KIND, name)
        return current
