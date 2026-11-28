# OkeyDocu - okeydocu/devices/instrument_check.py
# A test of an instrument: each part it offers is tried once, nothing is set and nothing measured.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable

from ..l10n import day, decimal, signed_seconds, tr
from ..model import DeviceIdentity
from .base import Capability, DeviceError, MeterDriver

OK, NOTE, FAILED = "ok", "note", "failed"  # a note does not keep the instrument from measuring
CLOCK_NOTE_S = 3.0
READING_S, LOW_BATTERY_MV = 30.0, 2500  # a sensor's wait for a reading; its battery runs low


@dataclass(frozen=True)
class Check:
    key: str
    title: str
    state: str
    detail: str = ""


@dataclass
class TestRun:
    identity: DeviceIdentity | None = None
    clock_offset_s: float | None = None
    checks: list[Check] | None = None

    @property
    def ready(self) -> bool:
        return all(check.state != FAILED for check in self.checks or [])


def run_checks(driver: MeterDriver, today: date,
               on_check: Callable[[Check], None] = lambda check: None,
               calibrated: bool = True) -> TestRun:
    """Stops at the first failure that leaves nothing more to try, such as no connection.
    An instrument not `calibrated` is said to be so instead of having its due date asked."""
    run = TestRun(checks=[])

    def report(key: str, title: str, state: str, detail: str = "") -> None:
        check = Check(key, title, state, detail)
        run.checks.append(check)
        on_check(check)

    started = time.monotonic()
    try:
        driver.open()
    except DeviceError as err:
        report("connect", tr("Connection"), FAILED, str(err))
        return run
    try:
        seconds = f"{time.monotonic() - started:.1f}"
        if Capability.TAKE not in driver.capabilities:  # a sensor connects to tell who it is
            report("connect", tr("Connection"), OK, tr("up after {seconds} s", seconds=seconds))
        _identity(driver, run, report, today, calibrated)
        if Capability.TAKE in driver.capabilities:
            _reading(driver, report)
        if Capability.CLOCK in driver.capabilities:
            _clock(driver, run, report)
        if Capability.SELECTOR in driver.capabilities:
            _selector(driver, report)
        if Capability.LIVE_RESULTS in driver.capabilities:
            _push(driver, report)
    finally:
        driver.close()
    return run


def _identity(driver, run: TestRun, report, today: date, calibrated: bool) -> None:
    try:
        who = run.identity = driver.identify()
    except DeviceError as err:
        report("identity", tr("Identity"), FAILED, str(err))
        return
    report("identity", tr("Identity"), OK,
           tr("{model}, serial number {serial}, firmware {firmware}",
              model=who.model, serial=who.serial_no, firmware=who.firmware))
    due = who.recalibration_due
    if not calibrated:
        report("calibration", tr("Calibration"), NOTE, tr("not calibrated, values for information"))
    elif due is None:
        report("calibration", tr("Calibration"), NOTE, tr("due date unknown"))
    elif who.calibration_overdue(today):
        report("calibration", tr("Calibration"), NOTE, tr("overdue since {day}", day=day(due)))
    else:
        report("calibration", tr("Calibration"), OK, tr("due on {day}", day=day(due)))


def _reading(driver, report) -> None:
    """Waits a bounded time for a whole reading of a sensor that measures when asked."""
    deadline = time.monotonic() + READING_S
    aborted = getattr(driver, "aborted", None)  # set from another thread to give up
    reading = None
    while time.monotonic() < deadline and not (aborted is not None and aborted.is_set()):
        reading, age, _ = driver.latest()
        if reading.complete and age < READING_S:
            break
        reading = None
        time.sleep(0.5)
    if reading is None:
        report("reading", tr("Reading"), FAILED, tr("The sensor has not sent a reading yet."))
        return
    text = tr("{temperature} \u00b0C, {humidity} % r.H.",
              temperature=decimal(reading.temperature, 1), humidity=decimal(reading.humidity, 0))
    if reading.battery_mv:
        text += ", " + tr("battery {volts} V", volts=decimal(reading.battery_mv / 1000, 2))
    low = reading.battery_mv is not None and reading.battery_mv < LOW_BATTERY_MV
    report("reading", tr("Reading"), NOTE if low else OK,
           text + (" \u2013 " + tr("replace the battery") if low else ""))


def _clock(driver, run: TestRun, report) -> None:
    try:
        offset = (driver.read_clock() - datetime.now()).total_seconds()
    except DeviceError as err:
        report("clock", tr("Clock"), FAILED, str(err))
        return
    run.clock_offset_s = offset
    if abs(offset) < CLOCK_NOTE_S:
        report("clock", tr("Clock"), OK, tr("is exact"))
    else:
        report("clock", tr("Clock"), NOTE,
               tr("is {offset} s off, set when a measurement starts", offset=signed_seconds(offset)))


def _selector(driver, report) -> None:
    try:
        position = driver.read_selector()
    except DeviceError as err:
        report("selector", tr("Rotary switch"), FAILED, str(err))
        return
    where = position.label or tr("an unknown position")
    report("selector", tr("Rotary switch"), OK, tr("set to {position}", position=where))


def _push(driver, report) -> None:
    """Switched on and off again; no measurement is waited for."""
    try:
        driver.subscribe_live(lambda reading: None)
        driver.unsubscribe_live()
    except DeviceError as err:
        report("push", tr("Push & Print"), FAILED, str(err))
        return
    report("push", tr("Push & Print"), OK, tr("switched on and off"))
