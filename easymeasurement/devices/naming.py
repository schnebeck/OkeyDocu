# EasyMeasurement - easymeasurement/devices/naming.py
# Settings of measurements in words: from the vocabulary, else from the instrument's own texts.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The application never reads an instrument's texts itself. A driver that has words for its
codes registers `InstrumentWords`; a code it recognises is named from the texts stored when
the instrument was set up, in the instrument's language that matches the current one."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from ..vocabulary import setting_name


@dataclass(frozen=True)
class InstrumentWords:
    driver: str
    is_code: Callable[[str], bool]
    culture: Callable[[], str]  # the instrument's language for the current one


class SettingWords:
    """For one screen or report: the texts are read once, on first need."""

    def __init__(self, db, sources: list[InstrumentWords]):
        self.db = db
        self.sources = sources
        self._texts: dict[str, dict[str, str]] = {}

    def _words(self, source: InstrumentWords) -> dict[str, str]:
        if source.driver not in self._texts:
            self._texts[source.driver] = self.db.device_texts(source.driver, source.culture())
        return self._texts[source.driver]

    def word(self, text: str) -> tuple[str, bool]:
        """The text in words, and whether it is: a code without a text stays a code."""
        for source in self.sources:
            if source.is_code(text):
                words = self._words(source)
                return words.get(text, text), text in words
        return text, True

    def say(self, key: str, value: str) -> tuple[str, str, bool]:
        """Name and value of a setting, and whether both could be put in words."""
        known = setting_name(key)
        name, named = (known, True) if known else self.word(key)
        shown, said = self.word(value)
        return name, shown, named and said
