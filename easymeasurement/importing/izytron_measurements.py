# EasyMeasurement - easymeasurement/importing/izytron_measurements.py
# Converts IZYTRON.IQ test steps into measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from ..devices.profitest_prime.mapping import is_conductor_setting, result_key
from ..l10n import N_
from ..model import (
    CONDUCTOR,
    SIGHT_CHECK_FUNCTION,
    MeterMeasurement,
    Parameter,
    Quantity,
    ResultValue,
    Verdict,
)
from ..vocabulary import plain, vocabulary

RANGE_MARKS = {1: ">", 2: "<"}  # RangerResult: the reading lies beyond the measuring range
ROTATION = {"rechts": "right", "links": "left"}
# IZYTRON names the function in the language it runs in.
FUNCTIONS = {
    "IΔN-UIΔN": "rcd_touch",
    "IΔN-ta": "rcd_time",
    "IF-UIΔN": "rcd_ramp_touch",
    "IF-IΔ": "rcd_current",
    "ZLN-ΔU": "zln_du",
    "RLO": "rlo",
    "RLO-25A": "rlo_25a",
    "RISO": "riso",
    "RISO-Rampe": "riso_ramp",
    "U": "u",
    "I_ZANGE": "i_clamp",
    "IL": "il",
    "IMD": "imd",
    "URES": "ures",
    "I_RAMP": "i_ramp",
    "RCM-UIΔN": "rcm_touch",
    "Zloop FW": "zloop",
    "Zloop+DC": "zloop_dc",
    "Zloop+Rlo": "zloop_rlo",
    "Zloop+0.5x": "zloop_half",
}
_LINE_VOLTAGES = {"u_l1l2", "u_l2l3", "u_l3l1"}


def _quantity_text(value: dict | None) -> str:
    """The text the instrument showed: mark, number at its precision, prefix, unit."""
    if not value or value.get("Value") is None:
        return ""
    number = f"{value['Value']:.{value.get('Precision') or 0}f}"
    mark = RANGE_MARKS.get(value.get("RangerResult"), "")
    return f"{mark}{number}{value.get('Prefix') or ''}{value.get('Unit') or ''}"


def _limit_text(limit: dict | None, mark: str) -> str:
    text = _quantity_text(limit)
    return f"{mark}{text}" if text else ""


def _result(entry: dict) -> ResultValue | None:
    raw = _quantity_text(entry.get("Value"))
    if not raw:
        return None
    code = (entry.get("TsKey") or "").removeprefix("PROFITEST_")
    key = result_key(code)
    known = vocabulary().results.get(key)
    label = entry.get("Description") or code
    if known is not None:
        label = plain(known.symbol) if known.symbol else known.name
    lower, upper = _limit_text(entry.get("Min"), ">"), _limit_text(entry.get("Max"), "<")
    verdict = Verdict.NOT_EVALUATED
    if lower or upper:
        verdict = Verdict.PASSED if entry.get("Result") == 0 else Verdict.FAILED
    return ResultValue(key, label, Quantity.parse(raw), verdict, lower, upper)


def _results(data: dict) -> tuple[ResultValue, ...]:
    results = []
    for main in data.get("MainMeasurements") or ():
        for entry in (main, *(main.get("BesideMeasurements") or ())):
            result = _result(entry)
            if result is not None:
                results.append(result)
        rotation = ROTATION.get(main.get("VerificationValue"))
        if rotation:
            results.append(
                ResultValue("rotation", "Drehfeld", Quantity(raw=rotation), Verdict.PASSED)
            )
    return tuple(results)


def _text(key: str, label: str, text: str) -> ResultValue:
    return ResultValue(key, label, Quantity(raw=text))


def _time(text: str) -> datetime:
    return datetime.fromisoformat(text[:19])


def _verdict(step) -> Verdict:
    return Verdict.PASSED if step["Has_Passed"] else Verdict.FAILED


def _device_measurement(step, data: dict, location: tuple[str, ...]) -> MeterMeasurement:
    results = _results(data)
    function = FUNCTIONS.get(step["Name"], step["Name"])
    if function == "u" and _LINE_VOLTAGES & {result.key for result in results}:
        function = "u3"
    return MeterMeasurement(
        uid=step["ID"].lower(), function=function, taken_at=_time(step["Date"]),
        verdict=_verdict(step), operator=step["Tester_Name"] or "", comment=step["Comment"] or "",
        location=location, results=results,
        parameters=tuple(_parameter(item) for item in data.get("Parameters") or ()),
        raw=step["Measurement_Data"],
    )


def _parameter(item: dict) -> Parameter:
    """Keyed by the instrument's code, as a push is, so both read the same; IZYTRON keeps
    the value as German text, which is shown as it stands."""
    code = (item.get("TsKey") or "").removeprefix("PROFITEST_")
    value = str(item.get("Value", ""))
    if is_conductor_setting(code):
        return Parameter(CONDUCTOR, value)
    return Parameter(code or item.get("Name", ""), value)


def _check_measurement(step, data: dict, location: tuple[str, ...]) -> MeterMeasurement:
    results = []
    for check in data.get("VisualInspections") or ():
        results.append(_text("question", N_("Inspection question"), check.get("Question") or ""))
        results.append(_text("answer", N_("Answer"), "yes" if check.get("Result") else "no"))
    if step["Comment"]:
        results.append(_text("note", N_("Remark"), step["Comment"]))
    return MeterMeasurement(
        uid=step["ID"].lower(), function=SIGHT_CHECK_FUNCTION, taken_at=_time(step["Date"]),
        verdict=_verdict(step), operator=step["Tester_Name"] or "",
        location=location, results=tuple(results), raw=step["Measurement_Data"],
    )
