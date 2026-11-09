# EasyMeasurement - easymeasurement/campaign/due.py
# What is due again: inspections whose interval runs out, and defects that wait for a follow-up.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from ..model import Verdict

LEAD_DAYS = 30  # this far ahead an inspection counts as due


def add_months(day: date, months: int) -> date:
    """The same day so many months later, or the month's last day if it has fewer."""
    month = day.month - 1 + months
    year, month = day.year + month // 12, month % 12 + 1
    return day.replace(year=year, month=month, day=min(day.day, monthrange(year, month)[1]))


@dataclass(frozen=True)
class DueInspection:
    asset_id: int
    asset: str
    kind: str
    customer: str
    last_campaign: int
    last_title: str
    last_day: date
    due: date
    months: int

    def overdue(self, today: date) -> bool:
        return self.due < today


@dataclass(frozen=True)
class OpenFollowUp:
    campaign_id: int
    title: str
    asset_id: int
    asset: str
    kind: str
    customer: str
    failed: int
    closed: date


class DueMixin:
    """Intervals belong to the element a campaign was made for, or to its kind."""

    def due_inspections(self, today: date | None = None) -> list[DueInspection]:
        today = today or date.today()
        rows = self.db.query(
            "SELECT c.id, c.title, c.closed_at, a.id AS asset_id, a.name, a.kind,"
            " a.interval_months AS own, k.interval_months AS usual, cu.name AS customer"
            " FROM campaigns c JOIN assets a ON a.id = c.asset_id"
            " JOIN customers cu ON cu.id = a.customer_id"
            " LEFT JOIN asset_kinds k ON k.key = a.kind"
            " WHERE c.status='closed' ORDER BY c.closed_at, c.id"
        )
        busy = {row["asset_id"] for row in self.db.query(
            "SELECT asset_id FROM campaigns WHERE status='open'")}
        latest = {row["asset_id"]: row for row in rows}  # the last one wins
        found = []
        for asset_id, row in latest.items():
            months = row["own"] if row["own"] is not None else (row["usual"] or 0)
            if not months or asset_id in busy:
                continue
            last = datetime.fromisoformat(row["closed_at"]).date()
            due = add_months(last, months)
            if due <= today + timedelta(days=LEAD_DAYS):
                found.append(DueInspection(asset_id, row["name"], row["kind"], row["customer"],
                                           row["id"], row["title"], last, due, months))
        return sorted(found, key=lambda item: item.due)

    def open_follow_ups(self) -> list[OpenFollowUp]:
        """Closed campaigns with failed measurements that no follow-up campaign refers to."""
        rows = self.db.query(
            "SELECT c.id, c.title, c.closed_at, a.id AS asset_id, a.name, a.kind,"
            " cu.name AS customer, (SELECT count(*) FROM measurements m"
            "   WHERE m.campaign_id = c.id AND m.verdict = ?) AS failed"
            " FROM campaigns c JOIN assets a ON a.id = c.asset_id"
            " JOIN customers cu ON cu.id = a.customer_id"
            " WHERE c.status='closed'"
            " AND NOT EXISTS (SELECT 1 FROM campaigns f WHERE f.follows_id = c.id)"
            " ORDER BY c.closed_at", Verdict.FAILED.value,
        )
        return [
            OpenFollowUp(row["id"], row["title"], row["asset_id"], row["name"], row["kind"],
                         row["customer"], row["failed"],
                         datetime.fromisoformat(row["closed_at"]).date())
            for row in rows if row["failed"]
        ]

    def mark_follow_up(self, campaign_id: int, follows_id: int) -> None:
        """Only an open campaign takes the mark; a sealed one is a record."""
        self.db.execute(
            "UPDATE campaigns SET follows_id=? WHERE id=? AND status='open'",
            follows_id, campaign_id,
        )
