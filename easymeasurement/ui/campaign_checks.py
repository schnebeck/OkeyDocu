# EasyMeasurement - easymeasurement/ui/campaign_checks.py
# What is left in an open campaign, said in the head with links to the rows concerned.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..model import Verdict
from ..campaign.repeat import REPEAT
from .common import POINT_ID, ROW_ID
from .structure_tree import UNPLACED

UNPLACED_LINK, FAILED_LINK, POINTS_LINK = "unplaced", "failed", "points"
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
        if campaign["plan_key"] == REPEAT:
            missing = sum(row["status"] in ("pending", "active")
                          for row, _ in self.app.service.points(campaign["id"]))
            if missing:
                parts.append(f'<a href="{POINTS_LINK}">{missing} offen</a>')
            if len(blockers) > (1 if missing else 0):
                parts.append(f'<span style="color:{ALERT}">Einstellung abweichend</span>')
        elif blockers:
            count = len(blockers)
            parts.append(f"{count} {'Punkt' if count == 1 else 'Punkte'} offen")
        if not blockers:
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
        elif link == POINTS_LINK:
            self._next_point()

    def _next_point(self) -> None:
        """Each click goes on to the next open point, the whole campaign in view."""
        self.structure.select(self._campaign()["asset_id"])
        table = self.values.table
        rows = [row for row in range(table.rowCount()) if table.item(row, 0).data(POINT_ID)]
        if rows:
            after = [row for row in rows if row > table.currentRow()]
            table.selectRow((after or rows)[0])
            table.scrollToItem(table.item((after or rows)[0], 0))

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
