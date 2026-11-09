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

# The instrument reports text IDs (TSnnnn). These tables follow its translation
# file. Unknown codes pass through unchanged rather than being guessed.
FUNCTION_CODES = {
    "TS1165": "riso",
    "TS1178": "i_clamp",
    "TS1285": "rlo",
    "TS1286": "u",
    "TS1287": "zln_du",
    "TS1289": "il",
    "TS1290": "imd",
    "TS1291": "ures",
    "TS1292": "i_ramp",
    "TS1294": "rcm_touch",
    "TS1296": "rcd_touch",
    "TS1297": "rcd_time",
    "TS1298": "rcd_ramp_touch",
    "TS1299": "rcd_current",
    "TS1417": "rlo_25a",
    "TS1607": "zloop",
    "TS1608": "zloop_dc",
    "TS1609": "zloop_rlo",
    "TS1610": "zloop_half",
    "TS1611": "riso_ramp",
}

RESULT_CODES = {
    "TS1159": ("rotation", "Drehfeld"),
    "TS1165": ("riso", "RISO"),
    "TS1170": ("u_iso", "UISO"),
    "TS1178": ("i_clamp", "I_ZANGE"),
    "TS1286": ("u", "U"),
    "TS1289": ("il", "IL"),
    "TS1348": ("u_idn", "UIΔN"),
    "TS1349": ("ta", "ta"),
    "TS1350": ("u_ln", "ULN"),
    "TS1351": ("f", "f"),
    "TS1352": ("re", "RE"),
    "TS1353": ("i_f", "IΔ"),
    "TS1354": ("zlpe", "ZLPE"),
    "TS1355": ("ik", "IK"),
    "TS1356": ("zln", "ZLN"),
    "TS1357": ("ue", "UE"),
    "TS1358": ("rlo", "RLO"),
    "TS1359": ("rlo_delta", "ΔRLO"),
    "TS1360": ("rlo_plus", "RLO+"),
    "TS1361": ("rlo_minus", "RLO-"),
    "TS1362": ("rlo_offset", "RLO-OFFSET"),
    "TS1363": ("u_lpe", "ULPE"),
    "TS1364": ("u_npe", "UNPE"),
    "TS1365": ("i", "I"),
    "TS1369": ("u_delta", "ΔU"),
    "TS1371": ("u_l3l1", "UL3L1"),
    "TS1372": ("u_l1l2", "UL1L2"),
    "TS1373": ("u_l2l3", "UL2L3"),
    "TS1632": ("zloop", "Z-AC"),
    "TS1633": ("z_dc", "Z-DC+"),
    "TS1634": ("z_rlo", "Z+RLO"),
    "TS1635": ("z_half", "Z-1/2xIdN"),
    "TS1655": ("z", "Z"),
}

# Stored as neutral words, never as text in one language: a report in any
# language has to be able to print them.
VERIFICATION_VALUES = {"TS1181": "left", "TS1182": "right", "TS1183": "error"}

# Which conductors a measurement was taken between. Every function has its own list.
CONDUCTOR_PARAMETERS = {"TS1225", "TS1245", "TS1261", "TS1264", "TS1274", "TS1275"}
CONDUCTORS = {
    "TS1326": "L-N",
    "TS1328": "AUTO",
    "TS1435": "L1-PE",
    "TS1436": "L2-PE",
    "TS1437": "L3-PE",
    "TS1438": "N-PE",
    "TS1439": "L+N-PE",
    "TS1440": "L1-N",
    "TS1441": "L2-N",
    "TS1442": "L3-N",
    "TS1443": "L1-L2",
    "TS1444": "L2-L3",
    "TS1445": "L1-L3",
}

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


def _parse_result(node: ET.Element) -> ResultValue:
    code = node.get("variable", "")
    key, label = RESULT_CODES.get(code, (code, code))
    lower, upper = node.get("lowerlimit", ""), node.get("upperlimit", "")
    # `passed` only means something next to a limit. Informational values such
    # as mains voltage come with passed="false" in measurements that passed.
    verdict = _verdict(node.get("passed")) if lower or upper else Verdict.NOT_EVALUATED
    quantity = Quantity.parse(node.get("value")) or Quantity(raw="")
    return ResultValue(key, label, quantity, verdict, lower, upper)


def _parse_verification(node: ET.Element) -> ResultValue:
    """A check against an expected outcome, such as the rotating field direction."""
    code = node.get("variable", "")
    key, label = RESULT_CODES.get(code, (code, code))
    value, setpoint = node.get("value", ""), node.get("setpoint", "")
    return ResultValue(
        key,
        label,
        Quantity(raw=VERIFICATION_VALUES.get(value, value)),
        _verdict(node.get("passed")),
        setpoint=VERIFICATION_VALUES.get(setpoint, setpoint),
    )


def _parameter(node: ET.Element) -> Parameter:
    code, value = node.get("description", ""), node.get("value", "")
    if code in CONDUCTOR_PARAMETERS:
        return Parameter(CONDUCTOR, CONDUCTORS.get(value, value))
    return Parameter(code, value)


def _function(code: str, results: tuple[ResultValue, ...]) -> str:
    function = FUNCTION_CODES.get(code, code)
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
