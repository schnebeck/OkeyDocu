# OkeyDocu - okeydocu/campaign/records.py
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
    """An empty name is left out: the record holds what the instrument tells, nothing more."""
    data = asdict(identity)
    if not data["name"]:
        del data["name"]
    return json.dumps(data, default=str, ensure_ascii=False)


def identity_from_json(text: str) -> DeviceIdentity | None:
    data = json.loads(text)
    if not data:
        return None
    for key in ("calibrated_on", "recalibration_due"):
        data[key] = date.fromisoformat(data[key]) if data.get(key) else None
    return DeviceIdentity(**data)


# A test begins with its first measurement, whenever its campaign was created; `tested_at`
# says so, and names the creation only while nothing is measured.
_CAMPAIGNS = ("SELECT c.*, coalesce((SELECT min(m.local_time) FROM measurements m"
              " WHERE m.campaign_id = c.id), c.started_at) AS tested_at FROM campaigns c")


class ReadingMixin:
    """Reading campaigns and what they recorded."""

    def campaign(self, campaign_id: int):
        return self.db.one(_CAMPAIGNS + " WHERE c.id=?", campaign_id)

    def campaigns(self, asset_id: int | None = None):
        """The test begun last comes first."""
        order = " ORDER BY tested_at DESC, c.id DESC"
        if asset_id is None:
            return self.db.query(_CAMPAIGNS + order)
        return self.db.query(_CAMPAIGNS + " WHERE c.asset_id=?" + order, asset_id)

    def test_days(self, campaign_id: int) -> tuple[date, date]:
        """The first and the last day measured on; answers of an inspection count as well.
        Until something is measured, the day the campaign was created stands in."""
        row = self.db.one(
            "SELECT min(local_time) AS first, max(local_time) AS last FROM measurements"
            " WHERE campaign_id=?", campaign_id)
        if row["first"] is None:
            created = datetime.fromisoformat(self.campaign(campaign_id)["started_at"]).date()
            return created, created
        return (datetime.fromisoformat(row["first"]).date(),
                datetime.fromisoformat(row["last"]).date())

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

    def unassigned_measurements(self, campaign_id: int):
        """Measurements that belong nowhere: to no step of a plan and to no element. One
        taken beside the plans and booked on an element is where it belongs."""
        return [row for row in self.open_measurements(campaign_id) if row["asset_id"] is None]

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
