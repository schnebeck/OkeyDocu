# EasyMeasurement - easymeasurement/reporting/measurement_words.py
# How a reading, its time and its marks are written in a report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re

from ..l10n import N_, in_language, tr
from ..model import is_conductor
from ..vocabulary import outcome_text
from .language import moment, value_text

GROUP = re.compile(r"^[A-Z][A-Za-z0-9]{0,7} - ")  # a short group name before the setting


def marks(measurement) -> str:
    """A record must not look measured or untouched if it is not."""
    found = [tr(text) for flag, text in ((measurement.manual, N_("manual")),
                                         (measurement.edited, N_("changed"))) if flag]
    return f" ({', '.join(found)})" if found else ""


def word(text: str) -> str:
    """A reading in the protocol's language: neutral words such as yes or right are
    translated, numbers are written with unit and prefix."""
    return value_text(in_language(outcome_text(text)))


def clock_times(measured) -> list[str]:
    """The time of each row, said only where it changes: answers saved together share one."""
    shown, last = [], None
    for measurement in measured:
        time = measurement.local_time.strftime("%H:%M:%S")
        shown.append((time if time != last else "") + marks(measurement))
        last = time
    return [text.strip() for text in shown]


def shared_time(measured) -> str:
    """The one moment several measurements share, none of them marked; else empty."""
    if len(measured) < 2 or any(m.manual or m.edited for m in measured):
        return ""
    moments = {m.local_time for m in measured}
    return moment(measured[0].local_time, seconds=True) if len(moments) == 1 else ""


def when(measurement) -> str:
    return moment(measurement.local_time, seconds=True) + marks(measurement)


def said_settings(words, parameters) -> list[tuple[str, str]]:
    """The instrument's settings in words; one still a code says nothing to a reader."""
    found = []
    for parameter in parameters:
        name, value, said = words.say(parameter.key, parameter.value)
        if not is_conductor(parameter) and said:
            found.append((name, value))
    return _without_group(found)


def _without_group(found: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """An instrument may name a setting with the group it belongs to, as in "RCD - Type". The
    measurement already says which function it is, so the group is left out; a name that would
    then stand twice, as the type of the RCD and of the mains, keeps its group, held to its
    name by spaces that do not break."""
    short = [GROUP.sub("", name) for name, _ in found]
    return [(full.replace(" - ", "\xa0-\xa0") if short.count(name) > 1 else name, value)
            for (full, value), name in zip(found, short)]
