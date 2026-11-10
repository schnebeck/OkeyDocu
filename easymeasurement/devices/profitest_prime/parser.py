# EasyMeasurement - easymeasurement/devices/profitest_prime/parser.py
# Turns the instrument's database XML into neutral measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import replace
from datetime import date, datetime

from ...model import (
    CONDUCTOR,
    DeviceIdentity,
    MeterMeasurement,
    Parameter,
    Quantity,
    ResultValue,
    Verdict,
)
from ...vocabulary import vocabulary
from .mapping import conductor, function_key, is_conductor_setting, outcome, result_key

# The instrument has one voltage function. A three-phase reading is what makes
# it a rotating field measurement.
_LINE_VOLTAGES = {"u_l1l2", "u_l2l3", "u_l3l1"}

_STRUCTURE = {
    "CUSTOMER",
    "MACHINE",
    "CIRCUIT",
    "DISTRIBUTIONCABINET",
    "RCD",
    "ELECTRICALEQUIPMENT",
    "MEASURINGPOINT",
}


def parse_date(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text) if text else None
    except ValueError:
        return None


def parse_identity(root: ET.Element) -> DeviceIdentity | None:
    node = root.find("TESTDEVICE")
    if node is None:
        return None
    return DeviceIdentity(
        manufacturer=node.get("manufacturer", ""),
        model=node.get("type", ""),
        serial_no=node.get("serialno", ""),
        firmware=node.get("firmware", ""),
        hardware=node.get("hardware", ""),
        order_no=node.get("orderno", ""),
        calibrated_on=parse_date(node.get("calibdate")),
        recalibration_due=parse_date(node.get("recalibdate")),
    )


def _verdict(passed: str | None) -> Verdict:
    return Verdict.PASSED if passed == "true" else Verdict.FAILED


def _label(key: str) -> str:
    """The vocabulary's symbol of a known result, kept for reading the record by itself;
    an unknown one keeps the instrument's code."""
    term = vocabulary().results.get(key)
    if term is None:
        return key
    return term.symbol or term.name


def _parse_result(node: ET.Element) -> ResultValue:
    key = result_key(node.get("variable", ""))
    label = _label(key)
    lower, upper = node.get("lowerlimit", ""), node.get("upperlimit", "")
    # `passed` only means something next to a limit. Informational values such
    # as mains voltage come with passed="false" in measurements that passed.
    verdict = _verdict(node.get("passed")) if lower or upper else Verdict.NOT_EVALUATED
    quantity = Quantity.parse(node.get("value")) or Quantity(raw="")
    return ResultValue(key, label, quantity, verdict, lower, upper)


def _parse_verification(node: ET.Element) -> ResultValue:
    """A check against an expected outcome, such as the rotating field direction."""
    key = result_key(node.get("variable", ""))
    value, setpoint = node.get("value", ""), node.get("setpoint", "")
    return ResultValue(
        key,
        _label(key),
        Quantity(raw=outcome(value)),
        _verdict(node.get("passed")),
        setpoint=outcome(setpoint),
    )


def _parameter(node: ET.Element) -> Parameter:
    code, value = node.get("description", ""), node.get("value", "")
    if is_conductor_setting(code):
        return Parameter(CONDUCTOR, conductor(value))
    return Parameter(code, value)


def _function(code: str, results: tuple[ResultValue, ...]) -> str:
    function = function_key(code)
    if function == "u" and _LINE_VOLTAGES & {result.key for result in results}:
        return "u3"
    return function


def _parse_measurement(node: ET.Element, location: tuple[str, ...]) -> MeterMeasurement:
    completed = node.get("completed") == "true"
    results = tuple(_parse_result(child) for child in node.findall("RESULT")) + tuple(
        _parse_verification(child) for child in node.findall("VERIFICATION")
    )
    return MeterMeasurement(
        uid=node.get("guid", ""),
        function=_function(node.get("type", ""), results),
        taken_at=datetime.fromisoformat(node.get("testdate", "")).replace(microsecond=0),
        verdict=_verdict(node.get("passed")) if completed else Verdict.NOT_EVALUATED,
        operator=node.get("tester", ""),
        comment=node.get("comment", ""),
        location=location,
        results=results,
        parameters=tuple(_parameter(child) for child in node if child.tag.endswith("PARAMETER")),
        raw=ET.tostring(node, encoding="unicode"),
    )


def parse_measurements(root: ET.Element) -> list[MeterMeasurement]:
    found: list[MeterMeasurement] = []

    def walk(node: ET.Element, path: tuple[str, ...]) -> None:
        for child in node:
            if child.tag == "MEASUREMENT":
                found.append(_parse_measurement(child, path))
            elif child.tag in _STRUCTURE:
                walk(child, path + (child.get("txt") or child.get("id") or child.tag,))

    database = root.find("DATABASE")
    if database is not None:
        walk(database, ())
    return found


def parse_event(frame: bytes) -> MeterMeasurement | None:
    """Read a Push/Print event, the same record as in the database but namespaced.

    The time is `testdate`: the event's own `timestamp` is off by a month.
    """
    root = ET.fromstring(frame)
    for node in root.iter():
        node.tag = node.tag.rsplit("}", 1)[-1]
    measurement = next((node for node in root.iter() if node.tag == "MEASUREMENT"), None)
    if measurement is None:
        return None
    return replace(_parse_measurement(measurement, ()), raw=frame.decode("utf-8", "replace"))


def parse_database(xml: bytes) -> tuple[DeviceIdentity | None, list[MeterMeasurement]]:
    root = ET.fromstring(xml)
    return parse_identity(root), parse_measurements(root)
