# EasyMeasurement - easymeasurement/campaign/instrument_history.py
# An instrument's history: its tests and the campaigns it measured in, by serial number.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime

from .records import MANUAL, identity_from_json

SIMULATOR = "simulator"


@dataclass(frozen=True)
class HistoryEntry:
    """One line of the history: a test (with its checks) or a campaign."""

    moment: str
    kind: str  # "test" or "campaign"
    title: str
    firmware: str
    calibrated_on: str
    recalibration_due: str
    clock_offset_s: float | None
    ready: bool | None = None
    checks: tuple = ()


def _day(value) -> str:
    return str(value) if value else ""


class InstrumentHistoryMixin:
    def save_instrument_test(self, driver: str, connection: str, run) -> int:
        """A test run stays as it was: the history is only ever added to."""
        who = run.identity
        return self.db.execute(
            "INSERT INTO instrument_tests (driver, connection, tested_at, model, serial_no,"
            " firmware, calibrated_on, recalibration_due, clock_offset_s, ready, checks_json)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            driver, connection, datetime.now().isoformat(timespec="seconds"),
            who.model if who else "", who.serial_no if who else "",
            who.firmware if who else "", _day(who and who.calibrated_on) or None,
            _day(who and who.recalibration_due) or None, run.clock_offset_s, int(run.ready),
            json.dumps([asdict(check) for check in run.checks], ensure_ascii=False),
        )

    def known_instruments(self) -> list[tuple[str, str]]:
        """(serial number, model) of every instrument tested or measured with, by serial."""
        found = {row["serial_no"]: row["model"] for row in self.db.query(
            "SELECT serial_no, model FROM instrument_tests WHERE serial_no <> ''")}
        for campaign in self._instrument_campaigns():
            who = identity_from_json(campaign["device_json"])
            if who and who.serial_no:
                found.setdefault(who.serial_no, who.model)
        return sorted(found.items())

    def instrument_history(self, serial_no: str) -> list[HistoryEntry]:
        """Newest first. A campaign shows what the instrument said at its start."""
        entries = [
            HistoryEntry(row["tested_at"], "test", "Test über " + (row["connection"] or "?"),
                         row["firmware"], row["calibrated_on"] or "",
                         row["recalibration_due"] or "", row["clock_offset_s"],
                         bool(row["ready"]), tuple(json.loads(row["checks_json"])))
            for row in self.db.query(
                "SELECT * FROM instrument_tests WHERE serial_no=?", serial_no)
        ]
        for campaign in self._instrument_campaigns():
            who = identity_from_json(campaign["device_json"])
            if who is None or who.serial_no != serial_no:
                continue
            entries.append(HistoryEntry(
                campaign["started_at"], "campaign", f"Kampagne „{campaign['title']}“",
                who.firmware, _day(who.calibrated_on), _day(who.recalibration_due),
                self._found_offset(campaign)))
        return sorted(entries, key=lambda entry: entry.moment, reverse=True)

    def _found_offset(self, campaign) -> float | None:
        """The clock as found at the start: before it was set, so its drift shows."""
        first = self.db.one(
            "SELECT kind, offset_s, offset_before_s FROM clock_checks WHERE campaign_id=?"
            " ORDER BY checked_at, id LIMIT 1", campaign["id"])
        if first is None:
            return campaign["clock_offset_s"]
        if first["kind"] == "set" and first["offset_before_s"] is not None:
            return first["offset_before_s"]
        return first["offset_s"]

    def _instrument_campaigns(self):
        """Measured or imported with a real instrument; a campaign by hand names none."""
        return self.db.query("SELECT * FROM campaigns WHERE driver NOT IN (?, ?)",
                             MANUAL, SIMULATOR)
