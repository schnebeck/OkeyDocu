# OkeyDocu - okeydocu/campaign/plan_blocks.py
# The plans of a campaign one by one: their progress, pausing, ending and removing one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Assigning a plan appends its steps behind those the campaign has, all with the plan's
title. So the steps of one assignment are a run of neighbouring positions with one title, and
two assignments of the same plan stay apart.

Pausing leaves every answer and reading where it is; only a step being measured stops
taking readings. Ending skips what is still open, with one reason for all. Removing takes the
steps with every reading and answer booked on them."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..l10n import tr
from ..store import CampaignClosed
from .plan_steps import TITLE_SEPARATOR
from .point_plans import has_points

OPEN = ("pending", "active")


@dataclass(frozen=True)
class PlanBlock:
    title: str
    step_ids: tuple[int, ...]
    done: int  # answered, measured or skipped

    @property
    def total(self) -> int:
        return len(self.step_ids)

    @property
    def finished(self) -> bool:
        return self.done == self.total


class PlanBlockMixin:
    def plan_blocks(self, campaign_id: int) -> list[PlanBlock]:
        """The test plans assigned, by their block id; steps without one go by title and
        neighbourhood. Points of a repeat or a template belong to no plan."""
        blocks: dict[str, PlanBlock] = {}
        last = ""
        for row in self.steps(campaign_id):
            step = self.plan_step(row)
            if step.origin:
                continue
            group = step.block or (last if last.startswith("~") and
                                   blocks[last].title == row["plan_title"] else f"~{row['id']}")
            last = group
            done = int(row["status"] not in OPEN)
            known = blocks.get(group)
            blocks[group] = (PlanBlock(known.title, (*known.step_ids, row["id"]), known.done + done)
                             if known else PlanBlock(row["plan_title"], (row["id"],), done))
        return list(blocks.values())

    def plan_step_rows(self, campaign_id: int) -> list:
        """The steps of test plans, without the points of a repeat or a template."""
        return [row for row in self.steps(campaign_id) if not self.plan_step(row).origin]

    def _retitle(self, campaign_id: int) -> None:
        """The campaign names where its points came from, then each plan."""
        points = next((row["plan_title"] for row in self.steps(campaign_id)
                       if self.plan_step(row).origin), "")
        titles = [points] if points else []
        titles += [block.title for block in self.plan_blocks(campaign_id)]
        self.db.execute("UPDATE campaigns SET plan_title=? WHERE id=?",
                        TITLE_SEPARATOR.join(titles), campaign_id)

    def first_open_step(self, block: PlanBlock) -> int:
        """Where working on a plan goes on; the first step once all are done."""
        marks = ",".join("?" * block.total)
        row = self.db.one(f"SELECT id FROM steps WHERE id IN ({marks}) AND status IN"
                          " ('pending', 'active') ORDER BY position LIMIT 1", *block.step_ids)
        return row["id"] if row else block.step_ids[0]

    def booked_on(self, block: PlanBlock) -> int:
        """Readings and answers that go with the plan's steps when it is removed."""
        marks = ",".join("?" * block.total)
        return self.db.one(f"SELECT count(*) AS n FROM measurements WHERE step_id IN ({marks})",
                           *block.step_ids)["n"]

    def pause_plans(self, campaign_id: int) -> None:
        """A step being measured goes back to waiting for its setup to be confirmed."""
        self._close_open_windows(campaign_id, datetime.now())
        self.db.execute("UPDATE steps SET status='pending' WHERE status='active'"
                        " AND campaign_id=?", campaign_id)

    def end_plan(self, block: PlanBlock, reason: str) -> None:
        for step_id in block.step_ids:
            if self.db.one("SELECT status FROM steps WHERE id=?", step_id)["status"] in OPEN:
                self.skip_step(step_id, reason)

    def remove_plan(self, campaign_id: int, block: PlanBlock) -> None:
        campaign = self.campaign(campaign_id)
        if campaign["status"] != "open":
            raise CampaignClosed(tr("The campaign is closed."))
        marks = ",".join("?" * block.total)
        for row in self.db.query(f"SELECT id FROM measurements WHERE step_id IN ({marks})",
                                 *block.step_ids):
            self.delete_measurement(row["id"])
        with self.db.transaction() as connection:
            connection.execute(f"DELETE FROM steps WHERE id IN ({marks})", block.step_ids)
        if not has_points(campaign["plan_key"]) and not self.plan_blocks(campaign_id):
            self.db.execute("UPDATE campaigns SET plan_key='' WHERE id=?", campaign_id)
        self._retitle(campaign_id)
