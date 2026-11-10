# EasyMeasurement - easymeasurement/model.py
# Device-neutral measurement types. Nothing here knows a specific instrument.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum

from .vocabulary import units


class Verdict(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    NOT_EVALUATED = "not_evaluated"


# Functions every installation of the program knows; the rest come from the vocabulary.
SIGHT_CHECK_FUNCTION = "visual_inspection"
UNREADABLE_FUNCTION = "unreadable"  # a record kept as it came, for a person to look at

_SI_PREFIX = {"µ": 1e-6, "u": 1e-6, "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9}
# Instruments send look-alikes: the PROFITEST PRIME writes the ohm sign U+2126,
# not the Greek omega. Units are compared in one spelling; `raw` keeps the original.
_UNIT_SPELLING = str.maketrans({"\u2126": "\u03a9", "\u03bc": "\u00b5"})
_QUANTITY_RE = re.compile(r"^\s*([<>≤≥]?)\s*(-?\d+(?:[.,]\d+)?)\s*(\S*)\s*$")


@dataclass(frozen=True)
class Quantity:
    """A reading as the instrument reported it, plus its value in base units.

    `raw` is what the report prints. `base_value` exists only so values can be
    compared and summarised, and is None when the text is not a number.
    """

    raw: str
    base_value: float | None = None
    base_unit: str = ""
    qualifier: str = ""

    @classmethod
    def parse(cls, text: str | None) -> "Quantity | None":
        if text is None or text == "":
            return None
        match = _QUANTITY_RE.match(text)
        if not match:
            return cls(raw=text)
        qualifier, number, unit = match.groups()
        unit = unit.translate(_UNIT_SPELLING)
        value = float(number.replace(",", "."))
        for base in units():
            if unit == base:
                return cls(text, value, base, qualifier)
            if unit.endswith(base) and unit[: -len(base)] in _SI_PREFIX:
                return cls(text, value * _SI_PREFIX[unit[: -len(base)]], base, qualifier)
        return cls(text, value, unit, qualifier)


@dataclass(frozen=True)
class ResultValue:
    key: str
    label: str
    quantity: Quantity
    verdict: Verdict = Verdict.NOT_EVALUATED
    lower_limit: str = ""
    upper_limit: str = ""
    setpoint: str = ""  # expected outcome of a check that has no numeric limit


@dataclass(frozen=True)
class Parameter:
    key: str
    value: str


CONDUCTOR = "conductor"


def conductor_of(parameters) -> str:
    """Between which conductors a measurement was taken, such as L1-PE."""
    for parameter in parameters:
        if parameter.key == CONDUCTOR or parameter.key.endswith("Leiter"):
            return parameter.value
    return ""


@dataclass(frozen=True)
class MeterMeasurement:
    """One stored measurement, in the instrument's own clock."""

    uid: str
    function: str
    taken_at: datetime
    verdict: Verdict
    operator: str = ""
    comment: str = ""
    location: tuple[str, ...] = ()
    results: tuple[ResultValue, ...] = ()
    parameters: tuple[Parameter, ...] = ()
    raw: str = ""  # the instrument's own record, kept as evidence

    def result(self, key: str) -> ResultValue | None:
        return next((r for r in self.results if r.key == key), None)


@dataclass(frozen=True)
class DeviceIdentity:
    manufacturer: str
    model: str
    serial_no: str
    firmware: str = ""
    hardware: str = ""
    order_no: str = ""
    calibrated_on: date | None = None
    recalibration_due: date | None = None

    def calibration_overdue(self, today: date) -> bool:
        return self.recalibration_due is not None and self.recalibration_due < today


@dataclass
class DeviceSnapshot:
    identity: DeviceIdentity
    measurements: list[MeterMeasurement] = field(default_factory=list)
