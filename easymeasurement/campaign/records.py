# EasyMeasurement - easymeasurement/campaign/records.py
# Constants of a campaign record and reading campaigns back.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path

from ..model import DeviceIdentity, MeterMeasurement, Parameter, Quantity, ResultValue, Verdict
from .plan import PlanStep
from .plan_language import told

MANUAL = "manual"
IMPORTED = "izytron"
NO_INSTRUMENT = (MANUAL, IMPORTED)  # nothing to connect to
# What may be overwritten. Value, unit and time are not on these lists, and the
# database refuses them as well.
EDITABLE_FIELDS = ("function", "location", "comment", "operator", "verdict", "hint")
EDITABLE_VALUE_FIELDS = ("label", "lower_limit", "upper_limit", "verdict")
# Fixing a text is everyday work. Whatever changes the meaning of a result is
# registered and marked in the report.
TEXT_FIELDS = ("location", "comment", "label", "hint")
LOCATION_SEPARATOR = " / "


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def full_name(user) -> str:
    return f"{user['title']} {user['name']}".strip()


def identity_to_json(identity: DeviceIdentity) -> str:
    return json.dumps(asdict(identity), default=str, ensure_ascii=False)


def identity_from_json(text: str) -> DeviceIdentity | None:
    data = json.loads(text)
    if not data:
        return None
    for key in ("calibrated_on", "recalibration_due"):
        data[key] = date.fromisoformat(data[key]) if data.get(key) else None
    return DeviceIdentity(**data)


class ReadingMixin:
    """Reading campaigns and what they recorded."""

    def campaign(self, campaign_id: int):
        return self.db.one("SELECT * FROM campaigns WHERE id=?", campaign_id)

    def campaigns(self, asset_id: int | None = None):
        if asset_id is None:
            return self.db.query("SELECT * FROM campaigns ORDER BY started_at DESC, id DESC")
        return self.db.query(
            "SELECT * FROM campaigns WHERE asset_id=? ORDER BY started_at DESC, id DESC", asset_id
        )

    def measurement_counts(self) -> dict[int, int]:
        rows = self.db.query(
            "SELECT campaign_id, count(*) AS total FROM measurements GROUP BY campaign_id"
        )
        return {row["campaign_id"]: row["total"] for row in rows}

    def steps(self, campaign_id: int):
        return self.db.query(
            "SELECT * FROM steps WHERE campaign_id=? ORDER BY position", campaign_id
        )

    def plan_step(self, step_row) -> PlanStep:
        """In the current language, as far as a catalogue knows its texts."""
        return PlanStep.from_dict(told(json.loads(step_row["plan_json"])))

    def measurements(self, campaign_id: int, step_id: int | None = None):
        if step_id is None:
            return self.db.query(
                "SELECT * FROM measurements WHERE campaign_id=? ORDER BY local_time, id", campaign_id
            )
        return self.db.query(
            "SELECT * FROM measurements WHERE step_id=? ORDER BY local_time, id", step_id
        )

    def open_measurements(self, campaign_id: int):
        return self.db.query(
            "SELECT * FROM measurements WHERE campaign_id=? AND step_id IS NULL"
            " ORDER BY local_time, id",
            campaign_id,
        )

    def values(self, measurement_id: int):
        return self.db.query(
            "SELECT * FROM measured_values WHERE measurement_id=? ORDER BY position, id",
            measurement_id,
        )

    def load_measurement(self, row) -> MeterMeasurement:
        results = tuple(
            ResultValue(
                value["key"],
                value["label"],
                Quantity(value["raw"], value["base_value"], value["base_unit"], value["qualifier"]),
                Verdict(value["verdict"]),
                value["lower_limit"],
                value["upper_limit"],
                value["setpoint"],
            )
            for value in self.values(row["id"])
        )
        return MeterMeasurement(
            uid=row["device_uid"],
            function=row["function"],
            taken_at=datetime.fromisoformat(row["device_time"] or row["local_time"]),
            verdict=Verdict(row["verdict"]),
            operator=row["operator"],
            comment=row["comment"],
            location=tuple(row["location"].split(LOCATION_SEPARATOR)) if row["location"] else (),
            results=results,
            parameters=tuple(Parameter(**p) for p in json.loads(row["parameters_json"])),
            raw=row["raw_data"],
        )

    def identity(self, campaign_id: int) -> DeviceIdentity:
        identity = identity_from_json(self.campaign(campaign_id)["device_json"])
        return identity or DeviceIdentity(manufacturer="", model="", serial_no="")

    def folder(self, campaign_id: int) -> Path:
        path = self.archive_root / "campaigns" / self.campaign(campaign_id)["uuid"]
        path.mkdir(parents=True, exist_ok=True)
        return path
