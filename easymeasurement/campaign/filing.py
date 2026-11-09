# EasyMeasurement - easymeasurement/campaign/filing.py
# Recording measurements, the step flow and filing what instruments deliver.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timedelta

from ..devices.base import LiveReading, MeterDriver
from ..model import DeviceIdentity, MeterMeasurement, ResultValue, Verdict
from .assignment import StepWindow, assign
from .records import LOCATION_SEPARATOR, MANUAL, _iso


class FilingMixin:
    """Measurements by hand or from an instrument, and the steps they belong to."""

    # Writing measurements ------------------------------------------------

    def _insert_measurement(
        self, campaign_id: int, measurement: MeterMeasurement, source: str, local_time: datetime,
        device_time: datetime | None, step_id: int | None, assignment: str, issue: str = "",
        identity: DeviceIdentity | None = None, clock_offset_s: float | None = None,
        received_at: datetime | None = None, asset_id: int | None = None,
    ) -> int:
        arrival = (received_at or datetime.now()).astimezone().isoformat(timespec="seconds")
        operator = measurement.operator
        if source.startswith("device:"):
            # The campaign's tester replaces the instrument's setting, which raw_data keeps.
            operator = self.campaign(campaign_id)["tester"] or operator
        with self.db.transaction() as connection:
            measurement_id = connection.execute(
                "INSERT INTO measurements (campaign_id, step_id, device_uid, source, function,"
                " device_time, local_time, verdict, operator, comment, location, parameters_json,"
                " assignment, issue, received_at, device_serial, firmware, raw_data, clock_offset_s,"
                " asset_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    campaign_id, step_id, measurement.uid, source, measurement.function,
                    _iso(device_time) if device_time else None, _iso(local_time),
                    measurement.verdict.value, operator, measurement.comment,
                    LOCATION_SEPARATOR.join(measurement.location),
                    json.dumps([asdict(p) for p in measurement.parameters], ensure_ascii=False),
                    assignment, issue, arrival,
                    identity.serial_no if identity else "",
                    identity.firmware if identity else "",
                    measurement.raw, clock_offset_s, asset_id,
                ),
            ).lastrowid
            for position, result in enumerate(measurement.results):
                quantity = result.quantity
                connection.execute(
                    "INSERT INTO measured_values (measurement_id, position, kind, key, label, raw,"
                    " base_value, base_unit, qualifier, lower_limit, upper_limit, setpoint,"
                    " verdict) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        measurement_id, position,
                        "number" if quantity.base_value is not None else "text",
                        result.key, result.label, quantity.raw, quantity.base_value,
                        quantity.base_unit, quantity.qualifier, result.lower_limit,
                        result.upper_limit, result.setpoint, result.verdict.value,
                    ),
                )
        return measurement_id

    def add_measurement(
        self, campaign_id: int, function: str, values: list[ResultValue],
        taken_at: datetime | None = None, verdict: Verdict = Verdict.NOT_EVALUATED,
        comment: str = "", location: str = "", step_id: int | None = None,
        asset_id: int | None = None,
    ) -> int:
        """Record a measurement by hand. Zero values are allowed."""
        moment = (taken_at or datetime.now()).replace(microsecond=0)
        measurement = MeterMeasurement(
            uid=str(uuid.uuid4()), function=function, taken_at=moment, verdict=verdict,
            operator=self.campaign(campaign_id)["tester"], comment=comment,
            location=(location,) if location else (), results=tuple(values),
        )
        return self._insert_measurement(
            campaign_id, measurement, MANUAL, moment, None, step_id, "manual", asset_id=asset_id
        )

    # Step flow -----------------------------------------------------------

    def _close_open_windows(self, campaign_id: int, now: datetime) -> None:
        self.db.execute(
            "UPDATE step_windows SET closed_at=? WHERE closed_at IS NULL AND step_id IN"
            " (SELECT id FROM steps WHERE campaign_id=?)",
            _iso(now), campaign_id,
        )

    def confirm_setup(self, step_id: int, now: datetime | None = None) -> None:
        now = now or datetime.now()
        step = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        self._close_open_windows(step["campaign_id"], now)
        self.db.execute(
            "UPDATE steps SET status='pending' WHERE status='active' AND campaign_id=?",
            step["campaign_id"],
        )
        self.db.execute("UPDATE steps SET status='active' WHERE id=?", step_id)
        self.db.execute(
            "INSERT INTO step_windows (step_id, opened_at) VALUES (?, ?)", step_id, _iso(now)
        )

    def finish_step(self, step_id: int, now: datetime | None = None) -> None:
        step = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        self._close_open_windows(step["campaign_id"], now or datetime.now())
        self.db.execute("UPDATE steps SET status='done' WHERE id=?", step_id)

    def skip_step(self, step_id: int, reason: str) -> None:
        step = self.db.one("SELECT * FROM steps WHERE id=?", step_id)
        self._close_open_windows(step["campaign_id"], datetime.now())
        if self.plan_step(step).kind == "check":
            self._forget_answer(step_id)
        self.db.execute("UPDATE steps SET status='skipped', note=? WHERE id=?", reason, step_id)

    # Collecting from an instrument --------------------------------------

    def _windows(self, campaign_id: int) -> list[StepWindow]:
        windows = []
        for step in self.steps(campaign_id):
            plan_step = self.plan_step(step)
            accepted = frozenset((plan_step.function, *plan_step.also_accepts))
            for row in self.db.query("SELECT * FROM step_windows WHERE step_id=?", step["id"]):
                closed = datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None
                windows.append(
                    StepWindow(step["id"], datetime.fromisoformat(row["opened_at"]), closed, accepted)
                )
        return windows

    def collect(self, campaign_id: int, driver: MeterDriver) -> dict:
        """Fetch from the instrument and file everything new. Safe to repeat."""
        return self.file_measurements(campaign_id, driver.read_measurements())

    def file_measurements(self, campaign_id: int, measurements: list[MeterMeasurement]) -> dict:
        campaign = self.campaign(campaign_id)
        baseline = set(json.loads(campaign["baseline_json"]))
        since = campaign["stored_since"]
        stored_since = datetime.fromisoformat(since) if since else None
        # What the operator deleted stays deleted, even though the instrument still has it.
        known = {
            row["device_uid"]
            for row in self.db.query(
                "SELECT device_uid FROM measurements WHERE source LIKE 'device:%'"
                " UNION SELECT device_uid FROM measurement_log WHERE action='delete'"
            )
        }
        identity = self.identity(campaign_id)
        offset = timedelta(seconds=campaign["clock_offset_s"])
        has_steps = bool(self.steps(campaign_id))
        windows = self._windows(campaign_id)
        added = assigned = 0
        for measurement in measurements:
            if measurement.uid in baseline or measurement.uid in known:
                continue
            if stored_since and measurement.taken_at < stored_since:
                continue
            local_time = measurement.taken_at - offset
            result = assign(local_time, measurement.function, windows) if has_steps else None
            step_id = result.step_id if result else None
            place = (self.place_for_path(campaign["asset_id"], measurement.location)
                     if measurement.location else None)
            self._insert_measurement(
                campaign_id, self._placed(measurement, place, campaign["asset_id"]),
                f"device:{campaign['driver']}", local_time, measurement.taken_at, step_id,
                "auto" if step_id else "open", result.issue if result else "", identity,
                campaign["clock_offset_s"], None, place,
            )
            added += 1
            assigned += 1 if step_id else 0
        return {"added": added, "assigned": assigned, "open": added - assigned}

    def _placed(self, measurement: MeterMeasurement, asset_id: int | None, root_id: int):
        """With an element to book it on, the measurement names that element as its place."""
        if asset_id is None:
            return measurement
        path = self.place_path(asset_id, root_id)
        return replace(measurement, location=tuple(path.split(LOCATION_SEPARATOR)))

    def receive(self, campaign_id: int, reading: LiveReading,
                asset_id: int | None = None) -> int | None:
        """Store a pushed measurement at once. The instrument keeps no copy of it.

        It goes to the step being worked on if it fits, otherwise it stays open
        for the operator: a question beats a wrong entry in a test record. A push
        brings no place of its own, so it lands on `asset_id`, the element chosen.
        """
        measurement = reading.measurement
        known = self.db.one(
            "SELECT 1 FROM measurements WHERE device_uid=? AND source LIKE 'device:%'",
            measurement.uid,
        )
        if known:
            return None
        campaign = self.campaign(campaign_id)
        offset = campaign["clock_offset_s"]
        local_time = measurement.taken_at - timedelta(seconds=offset)
        step_id, issue = None, ""
        if self.steps(campaign_id):
            result = assign(reading.received_at, measurement.function, self._windows(campaign_id))
            step_id, issue = result.step_id, result.issue
        return self._insert_measurement(
            campaign_id, self._placed(measurement, asset_id, campaign["asset_id"]),
            f"device:{campaign['driver']}", local_time, measurement.taken_at, step_id,
            "auto" if step_id else "open", issue, self.identity(campaign_id), offset,
            reading.received_at, asset_id,
        )

    def insert_imported(
        self, campaign_id: int, measurement: MeterMeasurement, source: str, local_time: datetime,
        device_time: datetime | None, identity: DeviceIdentity, clock_offset_s: float | None,
        asset_id: int | None,
    ) -> int:
        return self._insert_measurement(
            campaign_id, measurement, source, local_time, device_time, None, "open", "",
            identity, clock_offset_s, None, asset_id,
        )

    def date_import(self, campaign_id: int, started_at: datetime) -> None:
        """An import describes the past. It stays open for review, like any campaign."""
        self.db.execute("UPDATE campaigns SET started_at=? WHERE id=?", _iso(started_at), campaign_id)
