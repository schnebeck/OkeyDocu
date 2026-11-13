# OkeyDocu - okeydocu/campaign/runs.py
# Runs: steps measured as one named sequence, such as the questions of a visual inspection.
#
# A run can become a test plan of its own: each question a check, answered yes when in order,
# each other step a measurement of its function.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

import yaml

from ..model import SIGHT_CHECK_FUNCTION
from ..store.kinds import slug


class RunMixin:
    def add_run(self, campaign_id: int, name: str, kind: str, started_at: datetime,
                source_uid: str = "") -> int:
        return self.db.execute(
            "INSERT INTO runs (campaign_id, name, kind, source_uid, started_at)"
            " VALUES (?, ?, ?, ?, ?)",
            campaign_id, name, kind, source_uid, started_at.isoformat(timespec="seconds"),
        )

    def join_run(self, measurement_id: int, run_id: int, step_name: str = "") -> None:
        """The measurement becomes a step of the run; the step name says which one."""
        self.db.execute(
            "UPDATE measurements SET run_id=?, step_name=? WHERE id=?",
            run_id, step_name, measurement_id,
        )

    def run(self, run_id: int):
        return self.db.one("SELECT * FROM runs WHERE id=?", run_id)

    def plan_from_run(self, run_id: int) -> str:
        """Stores the run as a draft test plan and returns its title. A plan of the same name
        is kept; the new one gets a number."""
        run = self.run(run_id)
        steps = []
        for row in self.db.query("SELECT * FROM measurements WHERE run_id=? ORDER BY id", run_id):
            name = row["step_name"] or row["function"]
            key = slug(name)
            while key in {step["key"] for step in steps}:
                key += "_"
            if row["function"] == SIGHT_CHECK_FUNCTION:
                question = next((value["raw"] for value in self.values(row["id"])
                                 if value["key"] == "question"), name)
                steps.append({"key": key, "kind": "check", "title": name, "question": question})
            else:
                steps.append({"key": key, "title": name, "function": row["function"]})
        taken = {plan["title"] for plan in self.db.plans()}
        keys = {plan["key"] for plan in self.db.plans()}
        title, number = run["name"], 1
        while title in taken:
            number += 1
            title = f"{run['name']} ({number})"
        key = slug(title)
        while key in keys:
            key += "_"
        body = yaml.safe_dump({"key": key, "title": title, "released": False, "steps": steps},
                              allow_unicode=True, sort_keys=False)
        self.db.save_plan(key, title, body)
        return title
