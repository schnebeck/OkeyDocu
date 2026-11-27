# OkeyDocu - okeydocu/devices/climate/simulated.py
# A climate sensor that is not there: for trying out the guide without the hardware.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""It comes out of a warm pocket: its temperature falls from some degrees above the air
towards it and stands after a few seconds, so the settle station can be watched without
waiting a minute. Humidity follows the other way."""

from __future__ import annotations

import math
import random
import time
from datetime import datetime

from ...l10n import N_
from ...model import DeviceIdentity, MeterMeasurement
from ..base import Capability, DeviceError, LiveReading, MeterDriver
from ..driver_info import DriverInfo
from . import guides
from .driver import STALE_S, measurement
from .protocols import Reading
from .settling import Settling

KEY = "climate-simulator"
SPAN_S, PACE_S = 5.0, 3.0  # steady span, and how fast it takes on the air


class SimulatedClimate(MeterDriver):
    capabilities = Capability.LIVE_RESULTS | Capability.CLOCK | Capability.TAKE

    def __init__(self, port: str = "", **_):
        self.address = port or "sim-climate"
        self.air = round(random.uniform(18.0, 24.0), 1)
        self.humid = round(random.uniform(35.0, 55.0), 1)
        self.settling = Settling(span_s=SPAN_S)
        self.protocol = "simulated"
        self.started = 0.0
        self._on_reading = None

    def open(self) -> None:
        if not self.started:
            self.started = time.monotonic()

    def close(self) -> None:
        self.started = 0.0
        self.settling.restart()
        self._on_reading = None

    def _now(self) -> Reading:
        passed = time.monotonic() - self.started
        warm = 6.0 * math.exp(-passed / PACE_S)
        return Reading(round(self.air + warm, 2), round(self.humid - warm, 1), 2980, 95)

    def latest(self) -> tuple[Reading, float, float]:
        if not self.started:
            return Reading(), float("inf"), SPAN_S
        now = time.monotonic()
        reading = self._now()
        self.settling.add(now, reading.temperature)
        return reading, 0.0, self.settling.left_s(now)

    def identify(self) -> DeviceIdentity:
        return DeviceIdentity("OkeyDocu", N_("Simulated climate sensor"), self.address, "1.0")

    def point_out(self, seconds: int = 5) -> None:
        if not self.started:
            raise DeviceError(N_("The sensor is not in reach."))

    def read_clock(self) -> datetime:
        return datetime.now()

    def read_measurements(self) -> list[MeterMeasurement]:
        return []

    def subscribe_live(self, on_reading, on_state=None) -> None:
        self._on_reading = on_reading
        self.open()

    def unsubscribe_live(self) -> None:
        self._on_reading = None

    def take(self) -> MeterMeasurement:
        reading, age, _ = self.latest()
        if not reading.complete or age > STALE_S:
            raise DeviceError(N_("The sensor has not sent a reading yet."))
        taken = measurement(reading, datetime.now())
        if self._on_reading is not None:
            self._on_reading(LiveReading(taken, datetime.now()))
        return taken


DRIVER = DriverInfo(
    key=KEY,
    label=N_("Simulated climate sensor"),
    factory=SimulatedClimate,
    guide=guides.guide_for,
    guided=tuple(guides.GUIDES),
    simulated=True,
    companion=True,
    calibrated=False,
    advice=guides.hints,
    identity_of=lambda port: SimulatedClimate(port).identify(),
)
