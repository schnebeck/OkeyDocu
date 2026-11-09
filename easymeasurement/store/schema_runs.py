# EasyMeasurement - easymeasurement/store/schema_runs.py
# Runs: a named sequence of steps, such as a checklist of questions, measured as one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from .schema_parts import _frozen_with_its_campaign

# A measurement belongs to at most one run and is one of its steps there (`step_name`).
# A measurement on its own needs none; a function such as RISO is no run.
_RUNS = """
CREATE TABLE runs (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL DEFAULT '',
    source_uid TEXT NOT NULL DEFAULT '',
    started_at TEXT NOT NULL
);
CREATE INDEX runs_campaign ON runs(campaign_id);
CREATE INDEX measurements_run ON measurements(run_id);
""" + "".join(_frozen_with_its_campaign("runs"))
