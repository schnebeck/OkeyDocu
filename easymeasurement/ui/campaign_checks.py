# EasyMeasurement - easymeasurement/ui/campaign_checks.py
# What is left in an open campaign, said in the head with links to the rows concerned.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..model import Verdict
from .common import ROW_ID
from .structure_tree import UNPLACED

UNPLACED_LINK, FAILED_LINK = "unplaced", "failed"
ALERT, DONE = "#c0392b", "#27ae60"


class CampaignChecks:
    """Places missing, defects found and what stops the confirmation, in one line."""

    def _show_checks(self, campaign) -> None:
        label = self.header.checks
        if campaign is None or campaign["status"] != "open":
            label.setText("")
            return
        unplaced = self._count(campaign["id"], "asset_id IS NULL")
        failed = self._count(campaign["id"], "verdict = ?", Verdict.FAILED.value)
        blockers = self.app.service.blockers(campaign["id"])
        parts = []
        if unplaced:
            parts.append(f'<a href="{UNPLACED_LINK}">{unplaced} ohne Ort</a>')
        if failed:
            word = "Mangel" if failed == 1 else "Mängel"
            parts.append(f'<a href="{FAILED_LINK}" style="color:{ALERT}">{failed} {word}</a>')
        if blockers:
            count = len(blockers)
            parts.append(f"{count} {'Punkt' if count == 1 else 'Punkte'} offen")
        else:
            parts.append(f'<span style="color:{DONE}">✓ bereit zum Bestätigen</span>')
        label.setText("  ·  ".join(parts))
        label.setToolTip("\n".join(blockers))

    def _count(self, campaign_id: int, condition: str, *parameters) -> int:
        return self.app.db.one(
            f"SELECT count(*) AS n FROM measurements WHERE campaign_id = ? AND {condition}",
            campaign_id, *parameters,
        )["n"]

    def _follow_check(self, link: str) -> None:
        if link == UNPLACED_LINK:
            self.structure.select(UNPLACED)
        elif link == FAILED_LINK:
            self._next_defect()

    def _next_defect(self) -> None:
        """Each click goes on to the next defect, in the order they were measured."""
        rows = self.app.db.query(
            "SELECT id, asset_id FROM measurements WHERE campaign_id = ? AND verdict = ?"
            " ORDER BY local_time, id", self.campaign_id, Verdict.FAILED.value,
        )
        if not rows:
            return
        ids = [row["id"] for row in rows]
        current = self.values.table.currentItem()
        shown = self.values.table.item(current.row(), 0).data(ROW_ID) if current else None
        chosen = rows[(ids.index(shown) + 1) % len(rows)] if shown in ids else rows[0]
        place = chosen["asset_id"]
        self.structure.select(UNPLACED if place is None else place)
        self.values.select_measurement(chosen["id"])
