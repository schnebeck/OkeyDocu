# OkeyDocu - okeydocu/devices/simulator.py
# A software instrument for development, demos and tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import random
import uuid
from datetime import date, datetime, timedelta

from ..model import (
    DeviceIdentity,
    MeterMeasurement,
    Quantity,
    ResultValue,
    Verdict,
)
from ..l10n import N_, tr
from ..vocabulary import function_symbol
from .base import Capability, DeviceError, LiveReading, MeterDriver, SelectorPosition
from .driver_info import DriverInfo

_READINGS = {
    "rlo": lambda r: [("rlo", "RLO", f"{r.uniform(0.05, 0.6):.2f}Ω", "", "<1.00Ω")],
    "riso": lambda r: [
        ("riso", "RISO", f"{r.uniform(20, 900):.0f}MΩ", ">1.00MΩ", ""),
        ("u_iso", "UISO", f"{r.randint(510, 530)}V", "", ""),
    ],
    "u": lambda r: [("u", "U", f"{r.randint(226, 234)}V", "", ""), ("f", "f", "50.0Hz", "", "")],
    "u3": lambda r: [
        ("u_l3l1", "UL3L1", f"{r.randint(395, 405)}V", "", ""),
        ("u_l1l2", "UL1L2", f"{r.randint(395, 405)}V", "", ""),
        ("u_l2l3", "UL2L3", f"{r.randint(395, 405)}V", "", ""),
        ("f", "f", "50.0Hz", "", ""),
    ],
    "zloop": lambda r: [
        ("zloop", "Z-AC", f"{r.randint(60, 700)}mΩ", "", ""),
        ("ik", "IK", f"{r.uniform(0.3, 3.8):.2f}kA", "", ""),
        ("u_ln", "ULN", "230V", "", ""),
        ("f", "f", "50.0Hz", "", ""),
    ],
    "rcd_touch": lambda r: [
        ("u_idn", "UIΔN", f"{r.uniform(0.1, 3):.1f}V", "", "<50V"),
        ("u_ln", "ULN", "230V", "", ""),
    ],
    "rcd_time": lambda r: [
        ("ta", "ta", f"{r.randint(15, 280)}ms", ">0ms", "<300ms"),
        ("u_ln", "ULN", "230V", "", ""),
    ],
    "rcd_current": lambda r: [
        ("i_f", "IΔ", f"{r.uniform(16, 28):.1f}mA", ">15.0mA", "<30.0mA"),
        ("u_ln", "ULN", "230V", "", ""),
    ],
}


# Readings outside the limit, for the first limited value of a function.
_FAILING = {
    "rlo": lambda r: f"{r.uniform(1.1, 3):.2f}Ω",
    "riso": lambda r: f"{r.uniform(0.2, 0.95):.2f}MΩ",
    "rcd_touch": lambda r: f"{r.uniform(51, 70):.1f}V",
    "rcd_time": lambda r: f"{r.randint(310, 480)}ms",
    "rcd_current": lambda r: f"{r.uniform(30.5, 34):.1f}mA",
}

SIMULATED_FUNCTIONS = tuple(_READINGS)


class SimulatedMeter(MeterDriver):
    capabilities = (
        Capability.READ_STORED | Capability.CLOCK | Capability.SET_CLOCK
        | Capability.LIVE_RESULTS | Capability.SELECTOR | Capability.SIMULATED_TRIGGER
    )

    def __init__(
        self, clock_skew_s: float = 0.0, seed: int | None = None, overdue: bool = False,
        failure_rate: float = 0.0, settable_clock: bool = True,
    ):
        if not settable_clock:
            self.capabilities &= ~Capability.SET_CLOCK
        self._failure_rate = failure_rate
        self._skew = timedelta(seconds=clock_skew_s)
        self._random = random.Random(seed)
        self._overdue = overdue
        self._stored: list[MeterMeasurement] = []
        self._on_reading = None
        self.selector = ""  # the function the switch was last turned to

    def subscribe_live(self, on_reading, on_state=None) -> None:
        self._on_reading = on_reading

    def unsubscribe_live(self) -> None:
        self._on_reading = None

    def open(self) -> None:
        pass

    def close(self) -> None:
        self._on_reading = None

    def identify(self) -> DeviceIdentity:
        due = date(2020, 1, 1) if self._overdue else date.today() + timedelta(days=200)
        return DeviceIdentity(
            manufacturer="Simulator",
            model=tr("Virtual instrument"),
            serial_no="SIM-0001",
            firmware="1.0",
            calibrated_on=due - timedelta(days=365),
            recalibration_due=due,
        )

    def read_clock(self) -> datetime:
        return datetime.now() + self._skew

    def sync_clock(self) -> None:
        self._skew = timedelta()

    def read_measurements(self) -> list[MeterMeasurement]:
        return list(self._stored)

    def read_selector(self) -> SelectorPosition:
        if not self.selector:
            raise DeviceError(tr("The rotary switch has not been moved yet."))
        label = function_symbol(self.selector)
        return SelectorPosition(label, frozenset({self.selector}))

    def simulate_measurement(self, function: str, at: datetime | None = None) -> MeterMeasurement:
        """Store a reading, as if the operator had measured and pressed save."""
        self.selector = function
        taken_at = (at or datetime.now()) + self._skew
        failing = (
            function in _FAILING
            and self._failure_rate > 0
            and self._random.random() < self._failure_rate
        )
        results = []
        for key, label, text, lower, upper in _READINGS[function](self._random):
            limited = bool(lower or upper)
            verdict = Verdict.PASSED if limited else Verdict.NOT_EVALUATED
            if limited and failing:
                text, verdict = _FAILING[function](self._random), Verdict.FAILED
            results.append(ResultValue(key, label, Quantity.parse(text), verdict, lower, upper))
        if function == "u3":
            results.append(
                ResultValue(
                    "rotation", "Rotating field", Quantity(raw="right"), Verdict.PASSED,
                    setpoint="right",
                )
            )
        measurement = MeterMeasurement(
            uid=str(uuid.UUID(int=self._random.getrandbits(128))),
            function=function,
            taken_at=taken_at.replace(microsecond=0),
            verdict=Verdict.FAILED if failing else Verdict.PASSED,
            operator="Simulator",
            results=tuple(results),
        )
        # Like the real instrument: a pushed measurement is not kept in its memory.
        if self._on_reading is not None:
            self._on_reading(LiveReading(measurement, datetime.now()))
        else:
            self._stored.append(measurement)
        return measurement


DRIVER = DriverInfo("simulator", N_("Simulator (no hardware)"), SimulatedMeter, simulated=True)
