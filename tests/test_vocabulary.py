# EasyMeasurement - tests/test_vocabulary.py
# The application's vocabulary: names in the current language, and a new field of measurement
# added as a file of its own.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from easymeasurement import vocabulary as words
from easymeasurement.l10n import speaking
from easymeasurement.model import Quantity
from easymeasurement.vocabulary import terms

ACOUSTICS = """
quantities:
  sound_pressure_level: {unit: dB, name: Sound pressure level}
results:
  laeq: {symbol: LAeq, quantity: sound_pressure_level, name: Equivalent continuous level}
functions:
  sound_level: {symbol: Lp, name: Sound level at a workplace, results: [laeq]}
"""


@pytest.fixture
def with_files(tmp_path, monkeypatch):
    """The shipped vocabulary plus files of a test's own."""
    shipped = terms.folder()
    for entry in shipped.iterdir():
        (tmp_path / entry.name).write_text(entry.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(terms, "folder", lambda: tmp_path)
    terms.vocabulary.cache_clear()
    yield tmp_path
    terms.vocabulary.cache_clear()


def test_names_follow_the_language():
    with speaking("de"):
        assert words.function_label("rlo") == "RLO – Schutzleiterwiderstand"
        assert words.function_symbol("i_clamp") == "I_ZANGE"
        assert words.outcome_text("right") == "rechts"
        assert words.result_label("rotation", "Drehfeld") == "Drehfeld"
    with speaking("en"):
        assert words.function_label("rlo") == "RLO – Protective conductor resistance"
        assert words.result_label("rotation", "Drehfeld") == "Rotating field"


def test_what_the_vocabulary_does_not_know_stays_as_it_came():
    assert words.function_label("TS4711") == "TS4711"
    assert words.result_label("TS4712", "") == "TS4712"
    assert words.outcome_text("maybe") == "maybe"
    assert words.setting_name("TS4713") is None


def test_a_new_field_of_measurement_is_a_file_of_its_own(with_files):
    (with_files / "acoustics.yaml").write_text(ACOUSTICS, encoding="utf-8")
    assert "sound_level" in words.function_keys()
    assert words.function_label("sound_level") == "Lp – Sound level at a workplace"
    assert words.vocabulary().functions["sound_level"].results == ("laeq",)
    level = Quantity.parse("78.4dB")
    assert level.base_value == 78.4 and level.base_unit == "dB"


def test_a_key_defined_twice_is_refused(with_files):
    (with_files / "more.yaml").write_text("functions:\n  rlo: {name: Again}\n", encoding="utf-8")
    with pytest.raises(terms.VocabularyError, match="rlo"):
        words.vocabulary()


def test_an_unquoted_comma_is_found(with_files):
    (with_files / "more.yaml").write_text("results:\n  x: {name: One, two}\n", encoding="utf-8")
    with pytest.raises(terms.VocabularyError, match="unknown fields"):
        words.vocabulary()
