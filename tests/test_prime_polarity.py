# EasyMeasurement - tests/test_prime_polarity.py
# RLO in both current directions, delivered as the vocabulary's contract says.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from easymeasurement.devices.profitest_prime.polarity import by_direction
from easymeasurement.model import Quantity, ResultValue, Verdict


def figures(rlo, plus, minus, offset="0.00Ω"):
    found = [ResultValue("rlo", "RLO", Quantity.parse(rlo))] if rlo else []
    return tuple(found + [ResultValue("rlo_plus", "RLO+", Quantity.parse(plus)),
                          ResultValue("rlo_minus", "RLO-", Quantity.parse(minus)),
                          ResultValue("rlo_offset", "RLO-OFFSET", Quantity.parse(offset))])


def raw(results):
    return {result.key: result.quantity.raw for result in results}


def test_equal_directions_become_rlo_alone():
    assert raw(by_direction(figures("0.31Ω", "0.31Ω", "0.31Ω"))) == {
        "rlo": "0.31Ω", "rlo_offset": "0.00Ω"}
    assert raw(by_direction(figures("", "0.12Ω", "0.12Ω"))) == {
        "rlo": "0.12Ω", "rlo_offset": "0.00Ω"}


def test_directions_that_differ_leave_no_rlo_and_the_higher_leads():
    delivered = by_direction(figures("0.43Ω", "0.34Ω", "0.43Ω") + (
        ResultValue("rlo_delta", "dRLO", Quantity.parse("0.09Ω")),))
    assert [r.key for r in delivered] == ["rlo_minus", "rlo_plus", "rlo_offset"]
    assert raw(delivered) == {"rlo_minus": "0.43Ω", "rlo_plus": "0.34Ω", "rlo_offset": "0.00Ω"}


def test_the_reference_is_judged_by_the_limit_of_rlo():
    found = (ResultValue("rlo", "RLO", Quantity.parse("0.30Ω"), Verdict.PASSED, "", "<1.00Ω"),
             *figures("", "0.37Ω", "0.27Ω"))
    reference = by_direction(found)[0]
    assert (reference.key, reference.upper_limit, reference.verdict) == (
        "rlo_plus", "<1.00Ω", Verdict.PASSED)
    assert by_direction(figures("-0.02Ω", "-0.04Ω", "-0.02Ω"))[0].key == "rlo_minus"


def test_other_figures_pass_unchanged():
    others = (ResultValue("riso", "RISO", Quantity.parse(">1.20GΩ")),)
    assert by_direction(others) == others
