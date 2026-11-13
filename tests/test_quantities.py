# OkeyDocu - tests/test_quantities.py
# Readings written as number and unit with a prefix in steps of a thousand.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from okeydocu.l10n import speaking
from okeydocu.reporting.language import value_text

N = " "


def german(raw: str) -> str:
    with speaking("de"):
        return value_text(raw)


def test_the_number_stands_between_one_and_a_thousand():
    assert german("0.22Ω") == f"220{N}mΩ"
    assert german("1234Ω") == f"1,234{N}kΩ"
    assert german("0.5mA") == f"500{N}µA"
    assert german("519V") == f"519{N}V"


def test_no_digit_is_added_or_dropped():
    assert german("0.020Ω") == f"20{N}mΩ"
    assert german("1.20MΩ") == f"1,20{N}MΩ"
    assert german("50.0Hz") == f"50,0{N}Hz"


def test_zero_keeps_its_prefix_and_a_negative_number_a_true_minus():
    assert german("0.00mA") == f"0,00{N}mA"
    assert german("-0.02Ω") == f"−20{N}mΩ"


def test_a_reading_beyond_the_range_keeps_its_sign():
    assert german(">1.20GΩ") == f">{N}1,20{N}GΩ"
    assert german("<1µA") == f"<{N}1{N}µA"


def test_the_instruments_ohm_and_mu_are_read():
    assert german("0.22Ω") == f"220{N}mΩ"
    assert german("3μA") == f"3{N}µA"


def test_english_keeps_the_point_and_words_stay_as_they_are():
    with speaking("en"):
        assert value_text("1234Ω") == f"1.234{N}kΩ"
    assert german("rechts") == "rechts"
    assert german("100mV/mA") == f"100{N}mV/mA"


def test_a_clock_offset_has_its_sign_but_zero_has_none():
    from okeydocu.l10n import signed_seconds

    assert signed_seconds(3.4) == "+3"
    assert signed_seconds(-60.0) == "−60"
    assert signed_seconds(-0.3) == "0" and signed_seconds(0) == "0"
