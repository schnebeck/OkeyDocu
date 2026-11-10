# EasyMeasurement - tests/test_notation.py
# Symbols written as in mathematics, and what each figure of a result stands for.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from easymeasurement.l10n import speaking
from easymeasurement.vocabulary import (
    Role,
    counts,
    function_markup,
    markup,
    plain,
    result_label,
    result_markup,
    role,
)


def test_the_letter_is_italic_and_the_index_upright_and_low():
    assert markup("R_LO") == "<i>R</i><sub>LO</sub>"
    assert markup("ΔR_LO") == "Δ<i>R</i><sub>LO</sub>"
    assert markup("R_LO^+") == "<i>R</i><sub>LO</sub><sup>+</sup>"
    assert markup("U_L1-L2") == "<i>U</i><sub>L1-L2</sub>"


def test_words_and_units_stay_upright():
    assert markup("RCD U_IΔN") == "RCD <i>U</i><sub>IΔN</sub>"
    assert markup("R_LO 25 A") == "<i>R</i><sub>LO</sub> 25 A"
    assert markup("U3~") == "U3~"
    assert markup("Rotating field") == "Rotating field"
    assert markup("a<b") == "a&lt;b"


def test_without_type_styles_the_symbol_still_reads():
    assert plain("R_LO") == "RLO"
    assert plain("U_L1-L2") == "UL1-L2"
    assert plain("I_clamp") == "I_clamp"
    assert plain("R_LO,offset") == "RLO-offset"


def test_symbols_of_the_vocabulary_follow_the_language():
    with speaking("de"):
        assert result_label("rlo") == "RLO"
        assert result_markup("rlo") == "<i>R</i><sub>LO</sub>"
        assert result_markup("i_clamp") == "<i>I</i><sub>Zange</sub>"
        assert function_markup("riso") == "<i>R</i><sub>ISO</sub> – Isolationswiderstand"
        assert result_markup("unknown", "X<1") == "X&lt;1"


def test_a_figure_without_a_value_was_not_measured():
    assert role("rlo", "rlo", "---") is Role.NOT_MEASURED
    assert role("rlo", "rlo", "") is Role.NOT_MEASURED
    assert role("rlo", "rlo", "0.21Ω") is Role.RESULT


def test_the_lead_compensation_is_a_condition_of_rlo():
    assert role("rlo", "rlo_offset", "0.04Ω") is Role.CONDITION
    assert role("riso", "u_iso", "512V") is Role.CONDITION
    assert role("rcd_time", "ta", "18ms") is Role.RESULT


def test_the_polarities_count_only_where_rlo_did_not_pass():
    assert role("rlo", "rlo_plus", "0.21Ω") is Role.ON_FAIL
    assert not counts("rlo", "rlo_plus", "0.21Ω", passed=True)
    assert counts("rlo", "rlo_plus", "0.21Ω", passed=False)
    assert counts("rlo", "rlo_offset", "0.04Ω", passed=True)
    assert not counts("rlo", "rlo_minus", "---", passed=False)


def test_an_unknown_function_keeps_every_figure():
    assert role("TS9999", "rlo_plus", "1Ω") is Role.RESULT
