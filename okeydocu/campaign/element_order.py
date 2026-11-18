# OkeyDocu - okeydocu/campaign/element_order.py
# The order of elements side by side: moved one place, or put before or after another.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Siblings share a parent and a customer; `assets.position` orders them, the name breaks ties.
Every change numbers the siblings anew from 1, so equal positions never linger."""

from __future__ import annotations

_SIBLINGS = ("SELECT id FROM assets WHERE customer_id=? AND parent_id IS ?"
             " ORDER BY position, name COLLATE NOCASE, id")


class ElementOrderMixin:
    def siblings(self, asset_id: int) -> list[int]:
        """The element and those beside it, in their order."""
        asset = self.db.asset(asset_id)
        return [row["id"] for row in
                self.db.query(_SIBLINGS, asset["customer_id"], asset["parent_id"])]

    def _number(self, ordered: list[int]) -> None:
        with self.db.transaction() as connection:
            for position, asset_id in enumerate(ordered, start=1):
                connection.execute("UPDATE assets SET position=? WHERE id=?",
                                   (position, asset_id))

    def shift_element(self, asset_id: int, offset: int) -> None:
        """One place earlier (-1) or later (+1) among its siblings; at either end it stays."""
        ordered = self.siblings(asset_id)
        index = ordered.index(asset_id)
        other = index + offset
        if not 0 <= other < len(ordered):
            return
        ordered[index], ordered[other] = ordered[other], ordered[index]
        self._number(ordered)

    def place_element(self, asset_id: int, beside_id: int, after: bool) -> None:
        """Before or after another element, below that one's parent."""
        if asset_id == beside_id:
            return
        beside = self.db.asset(beside_id)
        if self.db.asset(asset_id)["parent_id"] != beside["parent_id"]:
            self.move_element(asset_id, beside["parent_id"])
        ordered = [i for i in self.siblings(beside_id) if i != asset_id]
        ordered.insert(ordered.index(beside_id) + int(after), asset_id)
        self._number(ordered)
