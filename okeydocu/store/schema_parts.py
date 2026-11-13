# OkeyDocu - okeydocu/store/schema_parts.py
# Tables and triggers the schema is put together from.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

_ASSET_COLUMNS = """
    kind TEXT NOT NULL REFERENCES asset_kinds(key) ON UPDATE CASCADE ON DELETE RESTRICT,
    name TEXT NOT NULL,
    identifier TEXT NOT NULL DEFAULT '',
    manufacturer TEXT NOT NULL DEFAULT '',
    type TEXT NOT NULL DEFAULT '',
    serial_no TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    guid TEXT NOT NULL DEFAULT '',
    features_json TEXT NOT NULL DEFAULT '{}',
    interval_months INTEGER,  -- NULL: as its kind says
    basis TEXT NOT NULL DEFAULT ''  -- what it is tested to; empty: as the element above
"""

# Kinds of structure elements and what can be noted about each, both editable. A choice list
# is a small table: its values are the rows, its attributes the columns, a fact one cell.
_KINDS = """
CREATE TABLE choice_lists (
    key TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    help TEXT NOT NULL DEFAULT '',  -- what the list is about, told above its values
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE choice_attributes (
    list TEXT NOT NULL REFERENCES choice_lists(key) ON UPDATE CASCADE ON DELETE CASCADE,
    name TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (list, name)
);

CREATE TABLE choice_values (
    id INTEGER PRIMARY KEY,
    list TEXT NOT NULL REFERENCES choice_lists(key) ON UPDATE CASCADE ON DELETE CASCADE,
    value TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0,
    help TEXT NOT NULL DEFAULT '',  -- what to know about the value, a few paragraphs
    curve TEXT NOT NULL DEFAULT '',  -- its time-current characteristic, such as "breaker 3 5"
    picture BLOB NOT NULL DEFAULT x'',  -- a picture of its own, PNG or SVG
    UNIQUE (list, value)
);

CREATE TABLE choice_facts (
    value_id INTEGER NOT NULL REFERENCES choice_values(id) ON DELETE CASCADE,
    attribute TEXT NOT NULL,
    text TEXT NOT NULL,
    PRIMARY KEY (value_id, attribute)
);

-- The measuring functions suited to an element that holds the value, and what to mind.
CREATE TABLE choice_methods (
    value_id INTEGER NOT NULL REFERENCES choice_values(id) ON DELETE CASCADE,
    function TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (value_id, function)
);

CREATE TABLE asset_kinds (
    key TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    icon TEXT NOT NULL DEFAULT 'element',
    izytron_type INTEGER,
    interval_months INTEGER NOT NULL DEFAULT 0,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE kind_features (
    id INTEGER PRIMARY KEY,
    kind TEXT NOT NULL REFERENCES asset_kinds(key) ON UPDATE CASCADE ON DELETE CASCADE,
    key TEXT NOT NULL,
    label TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    choice_list TEXT REFERENCES choice_lists(key) ON UPDATE CASCADE ON DELETE SET NULL,
    UNIQUE (kind, key)
);
"""

_MEASUREMENTS_FROZEN_UPDATE = """
CREATE TRIGGER measurements_frozen_update BEFORE UPDATE ON measurements
WHEN (SELECT status FROM campaigns WHERE id = OLD.campaign_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;
"""

_CAMPAIGN_NO_REOPEN = """
CREATE TRIGGER campaign_no_reopen BEFORE UPDATE ON campaigns
WHEN OLD.status = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;
"""

_VALUES_FROZEN_UPDATE = """
CREATE TRIGGER values_frozen_update BEFORE UPDATE ON measured_values
WHEN (SELECT c.status FROM campaigns c JOIN measurements m ON m.campaign_id = c.id
      WHERE m.id = OLD.measurement_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;
"""

# An instrument's GUID identifies one measurement, whichever campaign it reaches.
# A trigger rather than a unique index: it checks new rows and leaves existing ones alone.
_DEVICE_UID_ONCE = """
CREATE TRIGGER measurement_device_uid_once BEFORE INSERT ON measurements
WHEN NEW.source LIKE 'device:%' AND EXISTS (
    SELECT 1 FROM measurements WHERE device_uid = NEW.device_uid AND source LIKE 'device:%')
BEGIN SELECT RAISE(ABORT, 'measurement already stored'); END;
"""

# Every reading of the instrument's clock: the offset at that moment and how it came about.
_CLOCK_CHECKS_TABLE = """
CREATE TABLE clock_checks (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    checked_at TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('measured', 'set', 'manual')),
    offset_s REAL NOT NULL,
    offset_before_s REAL
);
"""



def _frozen_with_its_campaign(table: str) -> tuple[str, ...]:
    return tuple(
        f"""
CREATE TRIGGER {table}_frozen_{action.lower()} BEFORE {action} ON {table}
WHEN (SELECT status FROM campaigns WHERE id = {row}.campaign_id) = 'closed'
BEGIN SELECT RAISE(ABORT, 'campaign is closed'); END;
"""
        for action, row in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD"))
    )


_CLOCK_CHECKS_FROZEN = _frozen_with_its_campaign("clock_checks")

# A photo keeps the time it was taken at. `placement` says what decides where it belongs:
# the timeline, a person who pinned it to a measurement, or nothing yet on the stack.
_PHOTOS = """
CREATE TABLE photos (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    measurement_id INTEGER REFERENCES measurements(id) ON DELETE SET NULL,
    placement TEXT NOT NULL DEFAULT 'timeline'
        CHECK (placement IN ('timeline', 'pinned', 'stack')),
    file_name TEXT NOT NULL,
    original_name TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    taken_at TEXT,
    time_source TEXT NOT NULL DEFAULT 'unknown',
    role TEXT NOT NULL DEFAULT '' CHECK (role IN ('', 'hint', 'defect')),
    -- How it is shown: turned clockwise, then cut to "x y w h" in parts of the turned picture.
    rotation INTEGER NOT NULL DEFAULT 0 CHECK (rotation IN (0, 90, 180, 270)),
    crop TEXT NOT NULL DEFAULT '',
    UNIQUE (campaign_id, sha256)
);

CREATE INDEX photos_measurement ON photos(measurement_id);

-- From `at` on, in the time the photos were taken, the timeline runs `seconds` later.
CREATE TABLE photo_gaps (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    at TEXT NOT NULL,
    seconds REAL NOT NULL CHECK (seconds > 0)
);

-- Without a measurement and a place an attachment lies loose in its campaign.
CREATE TABLE attachments (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
    measurement_id INTEGER REFERENCES measurements(id) ON DELETE SET NULL,
    asset_id INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    kind TEXT NOT NULL CHECK (kind IN ('comment', 'image', 'pdf')),
    text TEXT NOT NULL DEFAULT '',
    file_name TEXT NOT NULL DEFAULT '',
    original_name TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    added_at TEXT NOT NULL
);

CREATE INDEX attachments_measurement ON attachments(measurement_id);
CREATE INDEX attachments_asset ON attachments(asset_id);
""" + "".join(
    statement for table in ("photos", "photo_gaps", "attachments")
    for statement in _frozen_with_its_campaign(table)
)

# What was measured stands: value, unit and time cannot be changed by anyone, also
# not by a bug further up. Everything else about a measurement can be overwritten,
# and the log says what it was before.
_READING_RULES = (
    """
CREATE TRIGGER reading_is_final BEFORE UPDATE OF raw, base_value, base_unit, qualifier, kind
ON measured_values
WHEN OLD.raw IS NOT NEW.raw OR OLD.base_value IS NOT NEW.base_value
     OR OLD.base_unit IS NOT NEW.base_unit OR OLD.qualifier IS NOT NEW.qualifier
     OR OLD.kind IS NOT NEW.kind
BEGIN SELECT RAISE(ABORT, 'reading is final'); END;
""",
    """
CREATE TRIGGER measurement_time_is_final BEFORE UPDATE OF device_time ON measurements
WHEN OLD.device_time IS NOT NEW.device_time
BEGIN SELECT RAISE(ABORT, 'reading is final'); END;
""",
)

_MEASUREMENT_LOG = (
    """
CREATE TABLE measurement_log (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER NOT NULL,
    measurement_id INTEGER NOT NULL,
    device_uid TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('edit', 'delete')),
    field TEXT NOT NULL DEFAULT '',
    old_value TEXT NOT NULL DEFAULT '',
    new_value TEXT NOT NULL DEFAULT ''
);
""",
    "CREATE INDEX measurement_log_measurement ON measurement_log(measurement_id);\n",
    """
CREATE TRIGGER measurement_log_no_update BEFORE UPDATE ON measurement_log
BEGIN SELECT RAISE(ABORT, 'log is append only'); END;
""",
    """
CREATE TRIGGER measurement_log_no_delete BEFORE DELETE ON measurement_log
BEGIN SELECT RAISE(ABORT, 'log is append only'); END;
""",
)

# Editable plans. A campaign copies the steps it gets, so a corrected plan changes no record.
_PLANS_TABLE = """
CREATE TABLE plans (
    id INTEGER PRIMARY KEY,
    key TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

_USERS_TABLE = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    name TEXT NOT NULL,
    signature BLOB,
    certificate_path TEXT NOT NULL DEFAULT '',
    certificate_name TEXT NOT NULL DEFAULT '',
    certificate_until TEXT NOT NULL DEFAULT '',
    archived INTEGER NOT NULL DEFAULT 0
);
"""

# A sealed campaign deleted on purpose leaves this behind, so the seal chain still holds.
# `seal_mac` authenticates the entry with the same key as the seals; it is only ever added to.
_DELETED_CAMPAIGNS = """
CREATE TABLE deleted_campaigns (
    id INTEGER PRIMARY KEY,
    uuid TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    seal TEXT NOT NULL,
    seal_mac TEXT NOT NULL DEFAULT '',
    deleted_at TEXT NOT NULL
);

CREATE TRIGGER deleted_campaigns_no_update BEFORE UPDATE ON deleted_campaigns
BEGIN SELECT RAISE(ABORT, 'deletions are kept'); END;

CREATE TRIGGER deleted_campaigns_no_delete BEFORE DELETE ON deleted_campaigns
BEGIN SELECT RAISE(ABORT, 'deletions are kept'); END;
"""
