# EasyMeasurement - easymeasurement/importing/izytron_source.py
# Reads an IZYTRON.IQ database read-only and rebuilds its asset tree.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path

from ..campaign.service import CampaignService
from ..l10n import tr
from ..model import DeviceIdentity

CUSTOMER_TYPE = 210
NOT_STRUCTURE = (0, CUSTOMER_TYPE)  # the database root and the customer
FALLBACK_KIND = "measuring_point"


def kinds_by_code(db) -> dict[int, str]:
    """IZYTRON object types onto the kinds that name them in the settings."""
    return {kind.izytron_type: kind.key for kind in db.kinds() if kind.izytron_type}


def _is_structure(row) -> bool:
    return row is not None and row["Object_Type"] not in NOT_STRUCTURE


class ImportFailed(Exception):
    """The database cannot be imported as it stands."""


class _Source:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.nodes = {
            row["Object_ID"].lower(): row
            for row in self.db.execute(
                "SELECT * FROM Hierarchical_Object WHERE Deleted=0 AND Object_ID IS NOT NULL"
            )
        }
        self.by_id = {row["ID"].lower(): row for row in self.nodes.values()}

    def customer(self):
        rows = self.db.execute("SELECT * FROM Customer WHERE Deleted=0").fetchall()
        if len(rows) != 1:
            raise ImportFailed(
                tr("Exactly one customer is expected, found: {count}.", count=len(rows)))
        return rows[0]

    def contact(self, customer_id: str):
        """The customer's first active contact person, where the database keeps them."""
        known = self.db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='Contact'").fetchone()
        if known is None:
            return None
        return self.db.execute(
            "SELECT * FROM Contact WHERE Customer_ID=? COLLATE NOCASE AND Deleted=0"
            " AND coalesce(Is_Active, 1)=1 ORDER BY Last_Name, First_Name LIMIT 1",
            (customer_id,),
        ).fetchone()

    def device_details(self, object_id: str):
        return self.db.execute(
            "SELECT * FROM Abstract_Device WHERE ID=? COLLATE NOCASE", (object_id,)
        ).fetchone()

    def steps(self):
        return self.db.execute(
            "SELECT s.*, t.Date, t.Name, t.Kind, t.Abstract_Device_ID, t.Tester_Name"
            " FROM Testing_Step s JOIN Testing t ON t.ID = s.Testing_ID COLLATE NOCASE"
            " WHERE s.Deleted=0 AND t.Deleted=0 ORDER BY t.Date, s.Step_Number"
        ).fetchall()

    def instrument(self, information: dict) -> DeviceIdentity:
        serial = information.get("SerialNumber", "")
        row = self.db.execute(
            "SELECT * FROM Testing_Device WHERE Serial_Number=?", (serial,)
        ).fetchone()
        calibrated = information.get("LastCalibrationDate")
        due = row["Next_Inspection"] if row else None
        return DeviceIdentity(
            manufacturer=information.get("Manufacturer", ""),
            model=information.get("DeviceType", ""),
            serial_no=serial,
            calibrated_on=date.fromisoformat(calibrated[:10]) if calibrated else None,
            recalibration_due=date.fromisoformat(due[:10]) if due else None,
        )


def _import_tree(source: _Source, service: CampaignService, customer_id: int) -> dict[str, int]:
    """Parents come first, however the rows are ordered."""
    assets: dict[str, int] = {}
    codes = kinds_by_code(service.db)
    fallback = FALLBACK_KIND if service.db.kind(FALLBACK_KIND) else service.db.kinds()[0].key
    pending = [row for row in source.nodes.values() if _is_structure(row)]

    def parent_of(row) -> str:
        return (row["Parent_ID"] or "").lower()

    while pending:
        waiting = []
        for row in pending:
            parent = source.by_id.get(parent_of(row))
            if _is_structure(parent):
                parent_asset = assets.get(parent["Object_ID"].lower())
                if parent_asset is None:
                    waiting.append(row)
                    continue
            else:
                parent_asset = None
            details = source.device_details(row["Object_ID"])
            assets[row["Object_ID"].lower()] = service.db.add_asset(
                customer_id, codes.get(row["Object_Type"], fallback),
                row["Designation"] or row["Designation2"] or tr("Unnamed"), parent_asset,
                identifier=row["Designation2"] or "",
                manufacturer=(details["Manufacturer"] if details else "") or "",
                type=(details["Type"] if details else "") or "",
                serial_no=(details["Serial_Number"] if details else "") or "",
                comment=(details["Remark"] if details else "") or "",
                guid=row["Object_ID"].lower(),
            )
        if len(waiting) == len(pending):
            raise ImportFailed(tr("The installation tree holds nodes without a reachable parent."))
        pending = waiting
    return assets


def _location(source: _Source, object_id: str) -> tuple[str, ...]:
    path = []
    row = source.nodes.get(object_id.lower())
    while _is_structure(row):
        path.append(row["Designation"] or row["Designation2"] or "")
        row = source.by_id.get((row["Parent_ID"] or "").lower())
    return tuple(reversed(path))
