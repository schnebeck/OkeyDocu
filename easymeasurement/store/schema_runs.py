# EasyMeasurement - easymeasurement/store/schema_runs.py
# Runs of steps measured as one, and the numbered marks drawn on photos.
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

# A region of a photo, numbered so a text can refer to it. Coordinates are fractions of the
# upright picture, so they hold at any size the photo is shown or printed in.
_PHOTO_MARKS = """
CREATE TABLE photo_marks (
    id INTEGER PRIMARY KEY,
    photo_id INTEGER NOT NULL REFERENCES photos(id) ON DELETE CASCADE,
    number INTEGER NOT NULL,
    x REAL NOT NULL,
    y REAL NOT NULL,
    w REAL NOT NULL,
    h REAL NOT NULL,
    text TEXT NOT NULL DEFAULT '',
    UNIQUE (photo_id, number)
);
""" + "".join(
    f"""
CREATE TRIGGER photo_marks_frozen_{action.lower()} BEFORE {action} ON photo_marks
WHEN (SELECT c.status FROM campaigns c JOIN photos p ON p.campaign_id = c.id
      WHERE p.id = {row}.photo_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;
"""
    for action, row in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD"))
)

# The firm that carries out the tests: one row, read by the report's letterhead.
_COMPANY = """
CREATE TABLE company (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    name TEXT NOT NULL DEFAULT '',
    street TEXT NOT NULL DEFAULT '',
    zip TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    web TEXT NOT NULL DEFAULT '',
    logo TEXT NOT NULL DEFAULT ''  -- base64 of the prepared image, as in templates
);
"""

# What an instrument calls its codes, in each language it knows, read when it is set up.
_DEVICE_TEXTS = """
CREATE TABLE device_texts (
    driver TEXT NOT NULL,
    language TEXT NOT NULL,  -- as the instrument names it, such as de-DE
    code TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (driver, language, code)
);

CREATE TABLE device_text_sets (
    driver TEXT PRIMARY KEY,
    firmware TEXT NOT NULL,  -- read from an instrument with this firmware
    version TEXT NOT NULL,
    read_at TEXT NOT NULL
);
"""

# Each test of an instrument, kept for good: together with the campaigns it is its history.
_INSTRUMENT_TESTS = """
CREATE TABLE instrument_tests (
    id INTEGER PRIMARY KEY,
    driver TEXT NOT NULL,
    connection TEXT NOT NULL DEFAULT '',  -- USB or Bluetooth
    tested_at TEXT NOT NULL,
    model TEXT NOT NULL DEFAULT '',
    serial_no TEXT NOT NULL DEFAULT '',  -- empty when the instrument could not be identified
    firmware TEXT NOT NULL DEFAULT '',
    calibrated_on TEXT,
    recalibration_due TEXT,
    clock_offset_s REAL,
    ready INTEGER NOT NULL,  -- fit to measure with
    checks_json TEXT NOT NULL  -- each check: key, title, state, detail
);
"""
