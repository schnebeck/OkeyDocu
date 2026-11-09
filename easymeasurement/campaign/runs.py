# EasyMeasurement - easymeasurement/campaign/runs.py
# Runs: steps measured as one named sequence, such as the questions of a visual inspection.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime


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
