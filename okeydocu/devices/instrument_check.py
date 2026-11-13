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

from ..l10n import day, signed_seconds, tr
from ..model import DeviceIdentity
from .base import Capability, DeviceError, MeterDriver

OK, NOTE, FAILED = "ok", "note", "failed"  # a note does not keep the instrument from measuring
CLOCK_NOTE_S = 3.0


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
               on_check: Callable[[Check], None] = lambda check: None) -> TestRun:
    """Stops at the first failure that leaves nothing more to try, such as no connection."""
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
        report("connect", tr("Connection"), OK, tr("up after {seconds} s", seconds=seconds))
        _identity(driver, run, report, today)
        if Capability.CLOCK in driver.capabilities:
            _clock(driver, run, report)
        if Capability.SELECTOR in driver.capabilities:
            _selector(driver, report)
        if Capability.LIVE_RESULTS in driver.capabilities:
            _push(driver, report)
    finally:
        driver.close()
    return run


def _identity(driver, run: TestRun, report, today: date) -> None:
    try:
        who = run.identity = driver.identify()
    except DeviceError as err:
        report("identity", tr("Identity"), FAILED, str(err))
        return
    report("identity", tr("Identity"), OK,
           tr("{model}, serial number {serial}, firmware {firmware}",
              model=who.model, serial=who.serial_no, firmware=who.firmware))
    due = who.recalibration_due
    if due is None:
        report("calibration", tr("Calibration"), NOTE, tr("due date unknown"))
    elif who.calibration_overdue(today):
        report("calibration", tr("Calibration"), NOTE, tr("overdue since {day}", day=day(due)))
    else:
        report("calibration", tr("Calibration"), OK, tr("due on {day}", day=day(due)))


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
