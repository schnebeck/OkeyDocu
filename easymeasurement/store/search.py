# EasyMeasurement - easymeasurement/store/search.py
# Search and filter across measurements, values and reports.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from .database import Database

_ASSET_TREE = """
WITH RECURSIVE tree(id) AS (
    SELECT id FROM assets WHERE id = ?
    UNION ALL
    SELECT a.id FROM assets a JOIN tree t ON a.parent_id = t.id
)
"""

_MEASUREMENT_COLUMNS = """
SELECT m.*, c.title AS campaign_title, c.tester, c.status AS campaign_status,
       a.id AS campaign_asset_id, a.name AS asset_name, a.identifier AS asset_identifier,
       cu.id AS customer_id, cu.name AS customer_name,
       (SELECT group_concat(v.label || ' ' || reading_text(v.raw), '   ') FROM measured_values v
        WHERE v.measurement_id = m.id) AS value_text,
       (SELECT v.base_value FROM measured_values v WHERE v.measurement_id = m.id
        ORDER BY v.position, v.id LIMIT 1) AS first_value,
       (SELECT count(*) FROM photos p WHERE p.measurement_id = m.id) AS photo_count
FROM measurements m
JOIN campaigns c ON c.id = m.campaign_id
JOIN assets a ON a.id = c.asset_id
JOIN customers cu ON cu.id = a.customer_id
"""


@dataclass
class MeasurementFilter:
    text: str = ""
    customer_id: int | None = None
    asset_id: int | None = None  # includes everything below this asset
    point_id: int | None = None  # where it was measured, including everything below
    unplaced: bool = False  # only measurements booked onto no element
    campaign_id: int | None = None
    step_id: int | None = None
    function: str | None = None
    verdict: str | None = None
    date_from: date | None = None
    date_to: date | None = None  # inclusive
    value_key: str | None = None
    value_min: float | None = None  # in base units, e.g. ohms
    value_max: float | None = None
    value_unit: str = ""  # keeps a bound in ohms from matching a reading in volts
    has_photo: bool | None = None


def _words(text: str) -> list[str]:
    return [word.casefold() for word in text.split()]


def _escape(word: str) -> str:
    return word.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_measurements(db: Database, query: MeasurementFilter, limit: int = 1000):
    """Every word must appear somewhere: customer, asset, campaign, comment or a value."""
    where: list[str] = []
    args: list = []
    prefix = ""
    if query.asset_id is not None:
        prefix = _ASSET_TREE
        args.append(query.asset_id)
        where.append("a.id IN (SELECT id FROM tree)")
    if query.point_id is not None:
        where.append(
            "m.asset_id IN (WITH RECURSIVE below(id) AS (SELECT ? UNION ALL"
            " SELECT p.id FROM assets p JOIN below b ON p.parent_id = b.id) SELECT id FROM below)"
        )
        args.append(query.point_id)
    if query.unplaced:
        where.append("m.asset_id IS NULL")
    if query.customer_id is not None:
        where.append("cu.id = ?")
        args.append(query.customer_id)
    if query.campaign_id is not None:
        where.append("c.id = ?")
        args.append(query.campaign_id)
    if query.step_id is not None:
        where.append("m.step_id = ?")
        args.append(query.step_id)
    if query.function:
        where.append("m.function = ?")
        args.append(query.function)
    if query.verdict:
        where.append("m.verdict = ?")
        args.append(query.verdict)
    if query.date_from:
        where.append("m.local_time >= ?")
        args.append(query.date_from.isoformat())
    if query.date_to:
        where.append("m.local_time < ?")
        args.append((query.date_to + timedelta(days=1)).isoformat())
    if query.has_photo is not None:
        exists = "EXISTS (SELECT 1 FROM photos p WHERE p.measurement_id = m.id)"
        where.append(exists if query.has_photo else f"NOT {exists}")
    if query.value_key or query.value_min is not None or query.value_max is not None:
        parts = ["v.measurement_id = m.id", "v.base_value IS NOT NULL"]
        if query.value_key:
            parts.append("v.key = ?")
            args.append(query.value_key)
        if query.value_unit:
            parts.append("v.base_unit = ?")
            args.append(query.value_unit)
        if query.value_min is not None:
            parts.append("v.base_value >= ?")
            args.append(query.value_min)
        if query.value_max is not None:
            parts.append("v.base_value <= ?")
            args.append(query.value_max)
        where.append(f"EXISTS (SELECT 1 FROM measured_values v WHERE {' AND '.join(parts)})")
    for word in _words(query.text):
        pattern = f"%{_escape(word)}%"
        fields = ("cu.name", "a.name", "a.identifier", "c.title", "c.tester", "m.comment",
                  "m.location", "m.function")
        clause = " OR ".join(f"fold({f}) LIKE ? ESCAPE '\\'" for f in fields)
        where.append(
            f"({clause} OR EXISTS (SELECT 1 FROM measured_values v WHERE v.measurement_id = m.id"
            " AND (fold(reading_text(v.raw)) LIKE ? ESCAPE '\\'"
            " OR fold(v.label) LIKE ? ESCAPE '\\'))"
            " OR EXISTS (SELECT 1 FROM photos p WHERE p.measurement_id = m.id"
            " AND fold(p.original_name) LIKE ? ESCAPE '\\'))"
        )
        args.extend([pattern] * (len(fields) + 3))
    sql = prefix + _MEASUREMENT_COLUMNS
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY m.local_time DESC, m.id DESC LIMIT ?"
    return db.query(sql, *args, limit)


def search_reports(
    db: Database, text: str = "", customer_id: int | None = None, asset_id: int | None = None,
    signed: bool | None = None, limit: int = 1000,
):
    where: list[str] = []
    args: list = []
    prefix = ""
    if asset_id is not None:
        prefix = _ASSET_TREE
        args.append(asset_id)
        where.append("a.id IN (SELECT id FROM tree)")
    if customer_id is not None:
        where.append("cu.id = ?")
        args.append(customer_id)
    if signed is not None:
        where.append("r.signed_by != ''" if signed else "r.signed_by = ''")
    for word in _words(text):
        fields = ("cu.name", "a.name", "a.identifier", "c.title", "c.tester", "r.template_name",
                  "r.signed_by")
        where.append("(" + " OR ".join(f"fold({f}) LIKE ? ESCAPE '\\'" for f in fields) + ")")
        args.extend([f"%{_escape(word)}%"] * len(fields))
    sql = prefix + (
        "SELECT r.*, c.title AS campaign_title, c.tester, a.name AS asset_name,"
        " cu.name AS customer_name FROM reports r JOIN campaigns c ON c.id = r.campaign_id"
        " JOIN assets a ON a.id = c.asset_id JOIN customers cu ON cu.id = a.customer_id"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.created_at DESC, r.id DESC LIMIT ?"
    return db.query(sql, *args, limit)
