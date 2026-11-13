# OkeyDocu - okeydocu/ui/campaign_checks.py
# What is left in an open campaign, said in the head with links to the rows concerned.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..model import Verdict
from ..campaign.repeat import REPEAT
from ..l10n import plural, tr
from .common import POINT_ID, ROW_ID
from .setting_warning import differing
from .structure_tree import UNPLACED

UNPLACED_LINK, FAILED_LINK, POINTS_LINK, STACK_LINK = "unplaced", "failed", "points", "stack"
SETTINGS_LINK = "settings"
ALERT, DONE, NOTE = "#c0392b", "#27ae60", "#d35400"


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
            text = tr("{count} without location", count=unplaced)
            parts.append(f'<a href="{UNPLACED_LINK}">{text}</a>')
        loose = len(self.app.service.stacked_photos(campaign["id"]))
        if loose:
            text = plural(loose, "{count} photo not assigned", "{count} photos not assigned")
            parts.append(f'<a href="{STACK_LINK}" style="color:{NOTE}">{text}</a>')
        if failed:
            text = plural(failed, "{count} defect", "{count} defects")
            parts.append(f'<a href="{FAILED_LINK}" style="color:{ALERT}">{text}</a>')
        set_apart = len(differing(self.app.db, campaign["id"]))
        if set_apart:
            text = plural(set_apart, "{count} set differently", "{count} set differently")
            parts.append(f'<a href="{SETTINGS_LINK}" style="color:{NOTE}">{text}</a>')
        if campaign["plan_key"] == REPEAT:
            missing = sum(row["status"] in ("pending", "active")
                          for row, _ in self.app.service.points(campaign["id"]))
            if missing:
                text = tr("{count} open", count=missing)
                parts.append(f'<a href="{POINTS_LINK}">{text}</a>')
            if len(blockers) > (1 if missing else 0):
                text = tr("Setting differs")
                parts.append(f'<span style="color:{ALERT}">{text}</span>')
        elif blockers:
            parts.append(plural(len(blockers), "{count} point open", "{count} points open"))
        if not blockers:
            text = tr("✓ ready to confirm")
            parts.append(f'<span style="color:{DONE}">{text}</span>')
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
        elif link == STACK_LINK:
            self.show_stack()
        elif link == SETTINGS_LINK:
            self._next_of(differing(self.app.db, self.campaign_id))

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
        self._next_of(self.app.db.query(
            "SELECT id, asset_id FROM measurements WHERE campaign_id = ? AND verdict = ?"
            " ORDER BY local_time, id", self.campaign_id, Verdict.FAILED.value,
        ))

    def _next_of(self, rows: list) -> None:
        """The measurement after the one shown, among `rows`; after the last, the first."""
        if not rows:
            return
        ids = [row["id"] for row in rows]
        current = self.values.table.currentItem()
        shown = self.values.table.item(current.row(), 0).data(ROW_ID) if current else None
        chosen = rows[(ids.index(shown) + 1) % len(rows)] if shown in ids else rows[0]
        place = chosen["asset_id"]
        self.structure.select(UNPLACED if place is None else place)
        self.values.select_measurement(chosen["id"])
