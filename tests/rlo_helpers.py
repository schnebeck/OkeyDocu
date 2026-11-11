# EasyMeasurement - tests/rlo_helpers.py
# RLO measurements and photos as the report tests use them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

from PIL import Image

from easymeasurement.devices.profitest_prime.polarity import by_direction
from easymeasurement.model import MeterMeasurement, Quantity, ResultValue, Verdict
from easymeasurement.reporting.context import ReportMeasurement

T0 = datetime(2026, 3, 1, 10, 0)


def rlo(value="0.21Ω", offset="0.04Ω", verdict=Verdict.PASSED, n=0, settings=None,
        directions=None):
    """As a driver delivers it: the directions in place of RLO where they differ."""
    plus, minus = directions or (value, value)
    results = by_direction((
        ResultValue("rlo", "RLO", Quantity.parse(value), verdict, "", "<1.00Ω"),
        ResultValue("rlo_plus", "RLO+", Quantity.parse(plus), verdict, "", "<1.00Ω"),
        ResultValue("rlo_minus", "RLO-", Quantity.parse(minus), verdict, "", "<1.00Ω"),
        ResultValue("rlo_offset", "RLO-OFFSET", Quantity.parse(offset)),
    ))
    data = MeterMeasurement(f"m{n}", "rlo", T0, verdict, results=results)
    shared = [("Polarität", "Automatisch"), ("Messdauer", "AUTO")]
    return ReportMeasurement(data, T0 + timedelta(minutes=n), settings=settings or shared)


def photo(path):
    Image.new("RGB", (400, 300), "steelblue").save(path, "JPEG")
    return path
