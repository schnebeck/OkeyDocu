# EasyMeasurement - tests/test_prime_parser.py
# Parsing the instrument's database and quantities. All instrument data is synthetic.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from easymeasurement.devices.profitest_prime.mapping import FUNCTIONS
from easymeasurement.devices.profitest_prime.parser import parse_database
from easymeasurement.model import Quantity, Verdict, conductor_of
from easymeasurement.vocabulary import function_keys

from .prime_helpers import DATABASE


def test_parser_maps_function_location_and_time():
    _, measurements = parse_database(DATABASE)
    riso = measurements[0]
    assert riso.function == "riso"
    assert riso.location == ("Kunde", "Maschine", "Schrank")
    assert riso.taken_at == datetime(2026, 1, 1, 9, 0, 5)
    assert riso.result("riso").quantity.base_value == pytest.approx(2.05e6)


def test_informational_value_with_passed_false_is_not_a_failure():
    _, measurements = parse_database(DATABASE)
    zloop = measurements[1]
    assert zloop.verdict is Verdict.PASSED
    assert zloop.result("u_ln").verdict is Verdict.NOT_EVALUATED


def test_limit_violation_and_unknown_codes_survive():
    _, measurements = parse_database(DATABASE)
    bad = measurements[2]
    assert bad.function == "TS9999"
    assert bad.verdict is Verdict.FAILED
    assert bad.result("TS8888").verdict is Verdict.FAILED


@pytest.mark.parametrize(
    "text,value,unit,qualifier",
    [
        ("2.05MΩ", 2.05e6, "Ω", ""),
        ("61mΩ", 0.061, "Ω", ""),
        ("3.76kA", 3760.0, "A", ""),
        ("121ms", 0.121, "s", ""),
        ("<3Ω", 3.0, "Ω", "<"),
        (">999MΩ", 999e6, "Ω", ">"),
        ("50.0Hz", 50.0, "Hz", ""),
    ],
)
def test_quantity_parsing(text, value, unit, qualifier):
    quantity = Quantity.parse(text)
    assert quantity.raw == text
    assert quantity.base_value == pytest.approx(value)
    assert (quantity.base_unit, quantity.qualifier) == (unit, qualifier)


# Codes of the instrument's translation file ---------------------------------


THREE_PHASE = """<?xml version="1.0" encoding="UTF-8"?><PROFITEST><DATABASE><CUSTOMER id="K"><MACHINE id="M">
<MEASUREMENT comment="" completed="true" guid="00000000-0000-1000-8000-000000000011" passed="true"
 testdate="2026-01-01T09:00:00.000" tester="Prüfer" type="TS1286">
<RESULT passed="true" value="398V" variable="TS1371"></RESULT>
<RESULT passed="true" value="399V" variable="TS1372"></RESULT>
<RESULT passed="true" value="400V" variable="TS1373"></RESULT>
<RESULT passed="true" value="50.0Hz" variable="TS1351"></RESULT>
<VERIFICATION passed="true" setpoint="TS1182" value="TS1182" variable="TS1159"></VERIFICATION>
</MEASUREMENT>
<MEASUREMENT comment="" completed="true" guid="00000000-0000-1000-8000-000000000012" passed="true"
 testdate="2026-01-01T09:01:00.000" tester="Prüfer" type="TS1286">
<RESULT passed="true" value="231V" variable="TS1286"></RESULT>
<RESULT passed="true" value="50.0Hz" variable="TS1351"></RESULT>
</MEASUREMENT>
</MACHINE></CUSTOMER></DATABASE></PROFITEST>""".encode()


def test_voltage_is_not_a_rotating_field_measurement():
    _, measurements = parse_database(THREE_PHASE)
    assert [m.function for m in measurements] == ["u3", "u"]
    assert measurements[1].result("u").quantity.raw == "231V"


def test_line_voltages_keep_the_instrument_order_and_names():
    three_phase = parse_database(THREE_PHASE)[1][0]
    assert [(r.key, r.label, r.quantity.raw) for r in three_phase.results[:3]] == [
        ("u_l3l1", "UL3-L1", "398V"),
        ("u_l1l2", "UL1-L2", "399V"),
        ("u_l2l3", "UL2-L3", "400V"),
    ]


def test_rotating_field_outcome_is_read_as_a_neutral_word():
    rotation = parse_database(THREE_PHASE)[1][0].result("rotation")
    assert (rotation.quantity.raw, rotation.setpoint) == ("right", "right")
    assert rotation.verdict is Verdict.PASSED


def test_every_function_of_the_instrument_has_a_neutral_name():
    assert len(FUNCTIONS) == 20
    assert set(FUNCTIONS.values()) <= set(function_keys())


def test_record_of_the_instrument_is_kept_with_the_measurement():
    measurement = parse_database(THREE_PHASE)[1][0]
    assert 'variable="TS1159"' in measurement.raw
    assert measurement.uid in measurement.raw


@pytest.mark.parametrize(
    "text, value, unit, qualifier",
    [
        (">1.20GΩ", 1.2e9, "Ω", ">"),
        ("2.05MΩ", 2.05e6, "Ω", ""),
        (">1.20G\u2126", 1.2e9, "Ω", ">"),  # the ohm sign the instrument really sends
        ("0.21\u2126", 0.21, "Ω", ""),
        ("350m\u2126", 0.35, "Ω", ""),
        ("<1µA", 1e-6, "A", "<"),
        ("<1\u03bcA", 1e-6, "A", "<"),
        (">199Ω", 199.0, "Ω", ">"),
    ],
)
def test_quantities_reach_base_units(text, value, unit, qualifier):
    quantity = Quantity.parse(text)
    assert quantity.base_value == pytest.approx(value)
    assert (quantity.base_unit, quantity.qualifier, quantity.raw) == (unit, qualifier, text)


def test_conductor_is_read_in_plain_words():
    frame = THREE_PHASE.replace(
        b'<RESULT passed="true" value="231V" variable="TS1286"></RESULT>',
        b'<TRANSLATEABLEPARAMETER description="TS1225" value="TS1443"></TRANSLATEABLEPARAMETER>'
        b'<RESULT passed="true" value="231V" variable="TS1286"></RESULT>',
    )
    measurement = parse_database(frame)[1][1]
    assert conductor_of(measurement.parameters) == "L1-L2"
