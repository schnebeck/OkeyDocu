# EasyMeasurement - easymeasurement/campaign/repeat.py
# A repeat inspection: what was recorded last time becomes the list of points to take again.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime

from ..model import FUNCTION_LABELS, SIGHT_CHECK_FUNCTION, Parameter, conductor_of
from .plan import Plan, PlanStep

REPEAT = "repeat"  # the plan key of a campaign whose steps came from the last inspection

_LAST_RECORD = """
SELECT m.*, r.name AS run_name, r.kind AS run_kind FROM measurements m
LEFT JOIN runs r ON r.id = m.run_id WHERE m.campaign_id = ? ORDER BY m.local_time, m.id
"""


def _parameters(text: str) -> list[Parameter]:
    return [Parameter(**item) for item in json.loads(text or "[]")]


def _short(function: str) -> str:
    return FUNCTION_LABELS.get(function, function).split(" – ")[0]


class RepeatMixin:
    def last_closed(self, asset_id: int):
        """The inspection of this installation to repeat: the last one confirmed."""
        return self.db.one(
            "SELECT * FROM campaigns WHERE asset_id=? AND status='closed'"
            " ORDER BY closed_at DESC, id DESC LIMIT 1", asset_id,
        )

    def repeat_plan(self, previous_id: int) -> Plan:
        """Every measurement and check of that inspection as a point, without its result."""
        previous = self.campaign(previous_id)
        steps = []
        for number, row in enumerate(self.db.query(_LAST_RECORD, previous_id), start=1):
            values = self.values(row["id"])
            texts = {value["key"]: value["raw"] for value in values}
            check = row["function"] == SIGHT_CHECK_FUNCTION
            question = texts.get("question", "")
            title = row["step_name"] or (question if check else _short(row["function"]))
            steps.append(PlanStep(
                key=f"r{number}", title=title, kind="check" if check else "measure",
                function=row["function"], asset_id=row["asset_id"],
                limits=tuple((v["key"], v["label"], v["lower_limit"], v["upper_limit"])
                             for v in values if v["lower_limit"] or v["upper_limit"]),
                parameters=tuple((p["key"], p["value"])
                                 for p in json.loads(row["parameters_json"] or "[]")),
                origin=f"{previous['uuid']}/{row['device_uid']}", hint=row["hint"],
                remark="  ".join(t for t in (row["comment"], texts.get("note", "")) if t),
                question=question, run=row["run_name"] or "", run_kind=row["run_kind"] or "",
            ))
        moment = datetime.fromisoformat(previous["closed_at"])
        return Plan(REPEAT, f"Wiederholung der Prüfung vom {moment:%d.%m.%Y}", True,
                    tuple(steps))

    def make_repeat(self, campaign_id: int, previous_id: int) -> None:
        self.assign_plan(campaign_id, self.repeat_plan(previous_id))
        self.rematch(campaign_id)

    def points(self, campaign_id: int) -> list[tuple]:
        """The points of a repeat inspection with their plan step, in their order."""
        return [(row, self.plan_step(row)) for row in self.steps(campaign_id)
                if self.plan_step(row).origin]

    def rematch(self, campaign_id: int) -> None:
        """Measurements take open points at their element, whatever order they come in.

        A point whose measurement went elsewhere or was deleted is open again.
        """
        campaign = self.campaign(campaign_id)
        if campaign is None or campaign["plan_key"] != REPEAT or campaign["status"] != "open":
            return
        points = self.points(campaign_id)
        by_step = {row["id"]: step for row, step in points}
        for taken in self.db.query(
            "SELECT id, step_id, asset_id FROM measurements WHERE campaign_id=? AND step_id"
            " IS NOT NULL", campaign_id,
        ):
            step = by_step.get(taken["step_id"])
            if step is not None and step.asset_id != taken["asset_id"]:
                self.db.execute("UPDATE measurements SET step_id=NULL, assignment='open'"
                                " WHERE id=?", taken["id"])
        filled = {row["step_id"] for row in self.db.query(
            "SELECT DISTINCT step_id FROM measurements WHERE campaign_id=? AND step_id IS NOT NULL",
            campaign_id)}
        status = {}
        for row, _ in points:
            status[row["id"]] = row["status"]
            if row["status"] == "done" and row["id"] not in filled:
                self.db.execute("UPDATE steps SET status='pending', note='' WHERE id=?", row["id"])
                status[row["id"]] = "pending"
        for loose in self.db.query(
            "SELECT id, asset_id, function, parameters_json FROM measurements WHERE"
            " campaign_id=? AND step_id IS NULL ORDER BY local_time, id", campaign_id,
        ):
            open_here = [(row, step) for row, step in points
                         if status[row["id"]] == "pending" and step.asset_id == loose["asset_id"]
                         and step.accepts(loose["function"])]
            if not open_here:
                continue
            # Several points of one kind on an element part by their conductors.
            conductor = conductor_of(_parameters(loose["parameters_json"]))
            row, step = next(
                ((row, step) for row, step in open_here
                 if conductor_of(Parameter(*item) for item in step.parameters) == conductor),
                open_here[0],
            )
            self.db.execute("UPDATE measurements SET step_id=?, assignment='auto' WHERE id=?",
                            row["id"], loose["id"])
            self.db.execute("UPDATE steps SET status='done' WHERE id=?", row["id"])
            status[row["id"]] = "done"
            self.took_point(row, step, loose["id"])

    def took_point(self, row, step: PlanStep, measurement_id: int) -> None:
        """A point taken: its hint goes on with the measurement, its run gathers it again."""
        if step.hint:
            self.db.execute("UPDATE measurements SET hint=? WHERE id=? AND hint=''",
                            step.hint, measurement_id)
        if step.run:
            run = self.db.one("SELECT id FROM runs WHERE campaign_id=? AND name=?",
                              row["campaign_id"], step.run)
            run_id = run["id"] if run else self.add_run(row["campaign_id"], step.run,
                                                        step.run_kind, datetime.now())
            self.join_run(measurement_id, run_id, step.title)

    def set_point_hint(self, step_id: int, hint: str) -> None:
        """Edited or dropped, the hint no longer goes on to this inspection's measurement."""
        row = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        step = replace(self.plan_step(row), hint=hint.strip())
        self.db.execute("UPDATE steps SET plan_json=? WHERE id=?",
                        json.dumps(step.to_dict(), ensure_ascii=False), step_id)

    def reopen_point(self, step_id: int) -> None:
        self.db.execute("UPDATE steps SET status='pending', note='' WHERE id=?", step_id)
        self.rematch(self.db.one("SELECT campaign_id FROM steps WHERE id=?", step_id)[0])

    def accept_deviation(self, step_id: int, reason: str) -> None:
        self.db.execute("UPDATE steps SET note=? WHERE id=?", reason.strip(), step_id)
