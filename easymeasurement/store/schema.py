# EasyMeasurement - easymeasurement/store/schema.py
# The complete schema of a current database.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from .schema_parts import (
    _ASSET_COLUMNS,
    _CAMPAIGN_NO_REOPEN,
    _CLOCK_CHECKS_FROZEN,
    _CLOCK_CHECKS_TABLE,
    _DELETED_CAMPAIGNS,
    _DEVICE_UID_ONCE,
    _KINDS,
    _MEASUREMENT_LOG,
    _MEASUREMENTS_FROZEN_UPDATE,
    _PHOTOS,
    _PLANS_TABLE,
    _READING_RULES,
    _USERS_TABLE,
    _VALUES_FROZEN_UPDATE,
)
from .schema_runs import _COMPANY, _DEVICE_TEXTS, _INSTRUMENT_TESTS, _PHOTO_MARKS, _RUNS

_SCHEMA = """
CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    street TEXT NOT NULL DEFAULT '',
    zip TEXT NOT NULL DEFAULT '',
    city TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT ''
);

""" + _KINDS + """
CREATE TABLE assets (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    parent_id INTEGER REFERENCES assets(id) ON DELETE RESTRICT,
""" + _ASSET_COLUMNS + """
);

""" + _USERS_TABLE + _COMPANY + _DEVICE_TEXTS + _INSTRUMENT_TESTS + """
CREATE TABLE campaigns (
    id INTEGER PRIMARY KEY,
    uuid TEXT NOT NULL UNIQUE,
    asset_id INTEGER NOT NULL REFERENCES assets(id) ON DELETE RESTRICT,
    plan_key TEXT NOT NULL,
    plan_title TEXT NOT NULL,
    title TEXT NOT NULL,
    tester TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'closed')),
    driver TEXT NOT NULL,
    device_json TEXT NOT NULL,
    clock_offset_s REAL NOT NULL DEFAULT 0,
    baseline_json TEXT NOT NULL DEFAULT '[]',
    stored_since TEXT,
    seal TEXT NOT NULL DEFAULT '',
    seal_previous TEXT NOT NULL DEFAULT '',
    seal_mac TEXT NOT NULL DEFAULT '',
    sealed_at TEXT,
    started_at TEXT NOT NULL,
    closed_at TEXT,
    user_id INTEGER REFERENCES users(id) ON DELETE RESTRICT,
    signature BLOB,
    photo_shift_s REAL NOT NULL DEFAULT 0,
    follows_id INTEGER,  -- the campaign whose defects this one follows up
    department TEXT NOT NULL DEFAULT '',  -- the customer's side of this job: where, and who
    contact TEXT NOT NULL DEFAULT '',
    contact_phone TEXT NOT NULL DEFAULT '',
    contact_email TEXT NOT NULL DEFAULT '',
    cost_center TEXT NOT NULL DEFAULT ''  -- the contractor's own account for this job
);

CREATE TABLE steps (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    plan_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'active', 'done', 'skipped')),
    note TEXT NOT NULL DEFAULT '',
    plan_title TEXT NOT NULL DEFAULT '',
    UNIQUE (campaign_id, position)
);

-- A step may be opened more than once, so its time windows are kept separately.
CREATE TABLE step_windows (
    id INTEGER PRIMARY KEY,
    step_id INTEGER NOT NULL REFERENCES steps(id) ON DELETE CASCADE,
    opened_at TEXT NOT NULL,
    closed_at TEXT
);

CREATE TABLE measurements (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    step_id INTEGER REFERENCES steps(id) ON DELETE SET NULL,
    device_uid TEXT NOT NULL,
    source TEXT NOT NULL,
    function TEXT NOT NULL,
    device_time TEXT,
    local_time TEXT NOT NULL,
    verdict TEXT NOT NULL,
    operator TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    parameters_json TEXT NOT NULL DEFAULT '[]',
    assignment TEXT NOT NULL DEFAULT 'open'
        CHECK (assignment IN ('auto', 'manual', 'open')),
    issue TEXT NOT NULL DEFAULT '',
    received_at TEXT,
    device_serial TEXT NOT NULL DEFAULT '',
    firmware TEXT NOT NULL DEFAULT '',
    raw_data TEXT NOT NULL DEFAULT '',
    clock_offset_s REAL,
    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    run_id INTEGER REFERENCES runs(id) ON DELETE SET NULL,
    step_name TEXT NOT NULL DEFAULT '',
    hint TEXT NOT NULL DEFAULT '',  -- how to measure here, for the next time; not printed
    UNIQUE (campaign_id, device_uid)
);

-- Every reading is a value: a number or a text.
CREATE TABLE measured_values (
    id INTEGER PRIMARY KEY,
    measurement_id INTEGER NOT NULL REFERENCES measurements(id) ON DELETE CASCADE,
    position INTEGER NOT NULL DEFAULT 0,
    kind TEXT NOT NULL CHECK (kind IN ('number', 'text')),
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    raw TEXT NOT NULL DEFAULT '',
    base_value REAL,
    base_unit TEXT NOT NULL DEFAULT '',
    qualifier TEXT NOT NULL DEFAULT '',
    lower_limit TEXT NOT NULL DEFAULT '',
    upper_limit TEXT NOT NULL DEFAULT '',
    setpoint TEXT NOT NULL DEFAULT '',
    verdict TEXT NOT NULL DEFAULT 'not_evaluated'
);

CREATE INDEX measured_values_measurement ON measured_values(measurement_id);
CREATE INDEX measured_values_key ON measured_values(key, base_value);
CREATE INDEX measurements_campaign ON measurements(campaign_id, local_time);
CREATE INDEX measurements_device_uid ON measurements(device_uid);

CREATE TABLE templates (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    body TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE reports (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE RESTRICT,
    template_name TEXT NOT NULL,
    template_body TEXT NOT NULL,
    file_name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    created_at TEXT NOT NULL,
    signed_by TEXT NOT NULL DEFAULT '',
    language TEXT NOT NULL DEFAULT 'de'
);

""" + _RUNS + _PHOTOS + _PHOTO_MARKS + _PLANS_TABLE + """
-- A closed campaign is a record: these triggers refuse every change to its data.
""" + _MEASUREMENTS_FROZEN_UPDATE + _CLOCK_CHECKS_TABLE + "".join(_CLOCK_CHECKS_FROZEN) + "".join(
    _READING_RULES + _MEASUREMENT_LOG
) + """
CREATE TRIGGER measurements_frozen_delete BEFORE DELETE ON measurements
WHEN (SELECT status FROM campaigns WHERE id = OLD.campaign_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;

CREATE TRIGGER measurements_frozen_insert BEFORE INSERT ON measurements
WHEN (SELECT status FROM campaigns WHERE id = NEW.campaign_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;

""" + _VALUES_FROZEN_UPDATE + _DEVICE_UID_ONCE + """
CREATE TRIGGER values_frozen_delete BEFORE DELETE ON measured_values
WHEN (SELECT c.status FROM campaigns c JOIN measurements m ON m.campaign_id = c.id
      WHERE m.id = OLD.measurement_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;

CREATE TRIGGER values_frozen_insert BEFORE INSERT ON measured_values
WHEN (SELECT c.status FROM campaigns c JOIN measurements m ON m.campaign_id = c.id
      WHERE m.id = NEW.measurement_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;

CREATE TRIGGER steps_frozen_update BEFORE UPDATE ON steps
WHEN (SELECT status FROM campaigns WHERE id = OLD.campaign_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;

""" + _CAMPAIGN_NO_REOPEN + _DELETED_CAMPAIGNS + """
-- Children go by cascade once the campaign row is gone, so this one trigger guards them all.
CREATE TRIGGER campaign_no_delete BEFORE DELETE ON campaigns
WHEN OLD.status = 'closed'
    AND NOT EXISTS (SELECT 1 FROM deleted_campaigns WHERE uuid = OLD.uuid)
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;
"""
