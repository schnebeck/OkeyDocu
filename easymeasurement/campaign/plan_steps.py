# EasyMeasurement - easymeasurement/campaign/plan_steps.py
# Plans of a campaign, and answering the points that are no measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json

from ..l10n import tr
from ..model import SIGHT_CHECK_FUNCTION, Quantity, ResultValue, Verdict
from ..store import CampaignClosed
from .plan import Plan, builtin_plan_texts, parse_plan

TITLE_SEPARATOR = " + "


class PlanStepMixin:
    """An answer is stored like any reading, so it shows and prints with the measurements."""

    def plans(self) -> list[Plan]:
        """The plans a campaign can get. One without points has nothing to offer yet."""
        plans = [parse_plan(row["body"]) for row in self.db.plans()]
        return [plan for plan in plans if plan.steps]

    def seed_plans(self) -> None:
        if not self.db.plans():
            for text in builtin_plan_texts():
                plan = parse_plan(text)
                self.db.save_plan(plan.key, plan.title, text)

    def _insert_steps(self, connection, campaign_id: int, plan: Plan) -> None:
        last = connection.execute(
            "SELECT max(position) FROM steps WHERE campaign_id=?", (campaign_id,)
        ).fetchone()[0]
        start = 0 if last is None else last + 1
        for position, step in enumerate(plan.steps, start):
            connection.execute(
                "INSERT INTO steps (campaign_id, position, plan_json, plan_title)"
                " VALUES (?, ?, ?, ?)",
                (campaign_id, position, json.dumps(step.to_dict(), ensure_ascii=False), plan.label),
            )

    def assign_plan(self, campaign_id: int, plan: Plan) -> None:
        """Add a plan's steps behind those the campaign already has."""
        campaign = self.campaign(campaign_id)
        if campaign["status"] != "open":
            raise CampaignClosed(tr("The campaign is closed."))
        titles = [campaign["plan_title"]] if campaign["plan_title"] else []
        with self.db.transaction() as connection:
            self._insert_steps(connection, campaign_id, plan)
            connection.execute(
                "UPDATE campaigns SET plan_key=?, plan_title=? WHERE id=?",
                (campaign["plan_key"] or plan.key, TITLE_SEPARATOR.join([*titles, plan.label]),
                 campaign_id),
            )

    def _forget_answer(self, step_id: int) -> None:
        for row in self.db.query("SELECT id FROM measurements WHERE step_id=?", step_id):
            self.delete_measurement(row["id"])

    def answer_step(self, step_id: int, answer: str, comment: str = "") -> None:
        """Record a yes or a no. Answering again replaces what was answered."""
        row = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        step = self.plan_step(row)
        self._forget_answer(step_id)
        verdict = Verdict.PASSED if answer == step.expected else Verdict.FAILED
        values = [
            ResultValue("question", "Prüffrage", Quantity(raw=step.question or step.title)),
            ResultValue("answer", "Antwort", Quantity(raw=answer), verdict, setpoint=step.expected),
        ]
        if comment:
            values.append(ResultValue("note", "Bemerkung", Quantity(raw=comment)))
        measurement_id = self.add_measurement(
            row["campaign_id"], SIGHT_CHECK_FUNCTION, values, verdict=verdict, step_id=step_id,
            asset_id=step.asset_id,
        )
        self.db.execute("UPDATE steps SET status='done', note='' WHERE id=?", step_id)
        self.took_point(row, step, measurement_id)

    def step_answer(self, step_id: int) -> tuple[str, str]:
        """The answer and comment given so far, empty if there are none."""
        row = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        if row["status"] == "skipped":
            return "skip", row["note"]
        found = {"answer": "", "note": ""}
        for measurement in self.measurements(row["campaign_id"], step_id):
            for value in self.values(measurement["id"]):
                if value["key"] in found:
                    found[value["key"]] = value["raw"]
        return found["answer"], found["note"]
