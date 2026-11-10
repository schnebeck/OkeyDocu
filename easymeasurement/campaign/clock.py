# EasyMeasurement - easymeasurement/campaign/clock.py
# The instrument's clock: offset, setting it, and the checks of a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..devices.base import Capability, DeviceError, MeterDriver
from ..model import DeviceIdentity
from .assignment import assign
from .records import NO_INSTRUMENT, _iso

# The instrument's clock loses about 35 s a month and does not follow daylight
# saving time. It is set before every campaign, so within one it barely moves;
# only a larger offset is worth bothering the operator with.
CLOCK_TOLERANCE_S = 30.0
# Reading the clock takes a moment and it counts whole seconds.
CLOCK_SET_ACCURACY_S = 3.0


class ClockState(Enum):
    SYNCED = "synced"
    OFFSET = "offset"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClockStatus:
    state: ClockState
    text: str


def measure_clock_offset(driver: MeterDriver) -> float:
    """How far the instrument's clock is ahead of the laptop, in seconds."""
    before = datetime.now()
    device_clock = driver.read_clock()
    after = datetime.now()
    return (device_clock - (before + (after - before) / 2)).total_seconds()


def clock_needs_setting(offset_s: float, driver: MeterDriver) -> bool:
    return abs(offset_s) >= CLOCK_TOLERANCE_S and Capability.SET_CLOCK in driver.capabilities


def set_instrument_clock(driver: MeterDriver) -> float:
    """Set the clock and verify it. Returns the offset it had before.

    An accepted command proves nothing: the instrument can answer time commands
    without changing anything.
    """
    before = measure_clock_offset(driver)
    driver.sync_clock()
    after = measure_clock_offset(driver)
    if abs(after) >= CLOCK_SET_ACCURACY_S:
        raise DeviceError(
            f"Die Uhr des Messgeräts ließ sich nicht stellen, sie weicht weiter um {after:+.0f} s"
            " ab. Bitte erneut versuchen."
        )
    return before


@dataclass(frozen=True)
class InstrumentStart:
    identity: DeviceIdentity
    offset_s: float
    offset_before_s: float | None
    stored_since: datetime


def read_instrument(driver: MeterDriver) -> InstrumentStart:
    """All a new campaign needs from the instrument. Touches no database.

    Sets the clock: with the clock right there is no offset to carry along. An
    instrument whose clock cannot be set keeps its measured offset.

    The instrument's memory is not read, which would take 15 s over Bluetooth
    and needs the rotary switch on Setup. Time tells old from new instead. If the
    clock ran ahead, a reading taken just before the start can look new. It then
    shows up as unassigned, which is better than silently dropping real ones.
    """
    identity = driver.identify()
    now = datetime.now().replace(microsecond=0)
    if Capability.SET_CLOCK in driver.capabilities:
        return InstrumentStart(identity, 0.0, set_instrument_clock(driver), now)
    offset = measure_clock_offset(driver)
    return InstrumentStart(identity, offset, None, now + timedelta(seconds=offset))


class ClockMixin:
    """The instrument's clock during a campaign."""

    def clock_checks(self, campaign_id: int):
        return self.db.query(
            "SELECT * FROM clock_checks WHERE campaign_id=? ORDER BY checked_at, id", campaign_id
        )

    def clock_status(self, campaign_id: int) -> ClockStatus | None:
        """What the last look at the clock showed. None without an instrument."""
        campaign = self.campaign(campaign_id)
        if campaign["driver"] in NO_INSTRUMENT:
            return None
        checks = self.clock_checks(campaign_id)
        if not checks:
            return ClockStatus(ClockState.UNKNOWN, "Geräteuhr nicht geprüft")
        last = checks[-1]
        moment = datetime.fromisoformat(last["checked_at"])
        if abs(last["offset_s"]) >= CLOCK_SET_ACCURACY_S:
            return ClockStatus(
                ClockState.OFFSET,
                f"Geräteuhr weicht {last['offset_s']:+.0f} s ab, Zeiten werden korrigiert",
            )
        action = {"set": "gestellt", "measured": "geprüft", "manual": "von Hand festgelegt"}
        return ClockStatus(
            ClockState.SYNCED,
            f"Geräteuhr synchron, {action[last['kind']]} um {moment:%H:%M:%S}",
        )

    def _record_clock(
        self, campaign_id: int, kind: str, offset_s: float, offset_before_s: float | None = None
    ) -> None:
        with self.db.transaction() as connection:
            connection.execute(
                "INSERT INTO clock_checks (campaign_id, checked_at, kind, offset_s,"
                " offset_before_s) VALUES (?, ?, ?, ?, ?)",
                (campaign_id, _iso(datetime.now()), kind, offset_s, offset_before_s),
            )
            connection.execute(
                "UPDATE campaigns SET clock_offset_s=? WHERE id=?", (offset_s, campaign_id)
            )

    def check_clock(self, campaign_id: int, driver: MeterDriver) -> float:
        """Measure the offset again. New measurements are converted with it."""
        offset = measure_clock_offset(driver)
        self.record_clock_check(campaign_id, offset)
        return offset

    def record_clock_check(self, campaign_id: int, offset_s: float) -> None:
        self._record_clock(campaign_id, "measured", offset_s)

    def record_clock_set(self, campaign_id: int, offset_before_s: float) -> None:
        self._record_clock(campaign_id, "set", 0.0, offset_before_s)

    def sync_device_clock(self, campaign_id: int, driver: MeterDriver) -> float:
        """Set the instrument's clock during a campaign.

        Measurements still on the instrument carry its old time, so they are
        fetched first. If that fails the clock stays as it is: afterwards
        nothing could tell which offset they belong to.
        """
        stored = driver.read_measurements()
        before = set_instrument_clock(driver)
        self.file_measurements(campaign_id, stored)
        self.record_clock_set(campaign_id, before)
        return 0.0

    def correct_clock_offset(self, campaign_id: int, offset_s: float) -> None:
        """State the offset by hand, for measurements from an earlier day.

        The offset depends on the date, so a value measured today can be wrong
        for them. Existing times are recalculated. `device_time` stays as it is.
        """
        # Set at the start is the normal case. Set later, the measurements of this
        # campaign rest on two different offsets.
        if any(check["kind"] == "set" for check in self.clock_checks(campaign_id)[1:]):
            raise DeviceError(
                "In dieser Kampagne wurde die Geräteuhr gestellt. Ein einzelner Versatz"
                " würde nicht für alle Messungen gelten."
            )
        rows = self.db.query(
            "SELECT * FROM measurements WHERE campaign_id=?"
            " AND device_time IS NOT NULL AND source LIKE 'device:%'",
            campaign_id,
        )
        previous = self.campaign(campaign_id)["clock_offset_s"]
        offset = timedelta(seconds=offset_s)
        windows = self._windows(campaign_id)
        with self.db.transaction() as connection:
            for row in rows:
                local_time = datetime.fromisoformat(row["device_time"]) - offset
                connection.execute(
                    "UPDATE measurements SET local_time=?, clock_offset_s=? WHERE id=?",
                    (_iso(local_time), offset_s, row["id"]),
                )
                # New times can fall into another step. A person's decision stays.
                if windows and row["assignment"] != "manual":
                    result = assign(local_time, row["function"], windows)
                    connection.execute(
                        "UPDATE measurements SET step_id=?, assignment=?, issue=? WHERE id=?",
                        (result.step_id, "auto" if result.step_id else "open", result.issue,
                         row["id"]),
                    )
        self._record_clock(campaign_id, "manual", offset_s, previous)
