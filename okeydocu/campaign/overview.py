# OkeyDocu - okeydocu/campaign/overview.py
# One line of figures per campaign, for the start screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..model import Verdict

# Correlated subqueries keep each figure independent; joins would multiply the counts.
_OVERVIEW = """
SELECT c.id, c.title, c.status, c.driver, c.tester, c.plan_title, c.plan_key,
       a.name AS asset, a.kind AS kind, k.name AS customer, k.city AS city,
       (SELECT count(*) FROM measurements m WHERE m.campaign_id = c.id) AS measured,
       (SELECT count(*) FROM measurements m WHERE m.campaign_id = c.id AND m.verdict = ?)
           AS failed,
       (SELECT count(*) FROM steps s WHERE s.campaign_id = c.id) AS steps,
       (SELECT count(*) FROM steps s WHERE s.campaign_id = c.id
            AND s.status IN ('done', 'skipped')) AS steps_done,
       (SELECT count(*) FROM measurements m WHERE m.campaign_id = c.id AND m.step_id IS NULL
            AND EXISTS (SELECT 1 FROM steps s WHERE s.campaign_id = c.id)) AS loose,
       (SELECT count(*) FROM reports r WHERE r.campaign_id = c.id) AS reports,
       max(c.started_at,
           coalesce(c.closed_at, ''),
           coalesce((SELECT max(m.local_time) FROM measurements m WHERE m.campaign_id = c.id), ''),
           coalesce((SELECT max(r.created_at) FROM reports r WHERE r.campaign_id = c.id), '')
       ) AS active_at
FROM campaigns c
JOIN assets a ON a.id = c.asset_id
JOIN customers k ON k.id = a.customer_id
"""


@dataclass(frozen=True)
class CampaignSummary:
    id: int
    title: str
    is_open: bool
    driver: str
    tester: str
    plan_title: str
    customer: str
    city: str
    asset: str
    measured: int
    failed: int
    steps: int
    steps_done: int
    loose: int
    reports: int
    active_at: datetime
    kind: str = ""

    def matches(self, words: list[str]) -> bool:
        """Every word somewhere in title, customer, place, asset, tester or plan."""
        text = " ".join(
            (self.title, self.customer, self.city, self.asset, self.tester, self.plan_title)
        ).casefold()
        return all(word in text for word in words)


class OverviewMixin:
    def summaries(self) -> list[CampaignSummary]:
        """Every campaign, the one worked on last first."""
        rows = self.db.query(_OVERVIEW, Verdict.FAILED.value)
        result = [
            CampaignSummary(
                id=row["id"], title=row["title"], is_open=row["status"] == "open",
                driver=row["driver"], tester=row["tester"],
                plan_title=row["plan_title"] if row["plan_key"] else "",
                customer=row["customer"], city=row["city"] or "", asset=row["asset"],
                measured=row["measured"], failed=row["failed"], steps=row["steps"],
                steps_done=row["steps_done"], loose=row["loose"], reports=row["reports"],
                active_at=datetime.fromisoformat(row["active_at"]), kind=row["kind"],
            )
            for row in rows
        ]
        return sorted(result, key=lambda summary: (summary.active_at, summary.id), reverse=True)
