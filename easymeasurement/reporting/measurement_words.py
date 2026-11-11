# EasyMeasurement - easymeasurement/reporting/measurement_words.py
# How a reading, its time and its marks are written in a report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..l10n import N_, in_language, tr
from ..model import is_conductor
from ..vocabulary import outcome_text
from .language import moment, value_text


def marks(measurement) -> str:
    """A record must not look measured or untouched if it is not."""
    found = [tr(text) for flag, text in ((measurement.manual, N_("manual")),
                                         (measurement.edited, N_("changed"))) if flag]
    return f" ({', '.join(found)})" if found else ""


def word(text: str) -> str:
    """A reading in the protocol's language: neutral words such as yes or right are
    translated, numbers are written with unit and prefix."""
    return value_text(in_language(outcome_text(text)))


def when(measurement) -> str:
    return moment(measurement.local_time, seconds=True) + marks(measurement)


def said_settings(words, parameters) -> list[tuple[str, str]]:
    """The instrument's settings in words; one still a code says nothing to a reader."""
    found = []
    for parameter in parameters:
        name, value, said = words.say(parameter.key, parameter.value)
        if not is_conductor(parameter) and said:
            found.append((name, value))
    return found
