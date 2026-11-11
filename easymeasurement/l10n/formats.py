# EasyMeasurement - easymeasurement/l10n/formats.py
# Dates, times and decimal numbers as the current language writes them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime

DEFAULTS = {
    "date": "%Y-%m-%d",
    "time": "%H:%M:%S",
    "short_time": "%H:%M",
    "decimal": ".",
}
EMPTY = "–"


def pattern(name: str) -> str:
    from . import active

    return active().formats.get(name, DEFAULTS[name])


def day(value: date | None) -> str:
    return value.strftime(pattern("date")) if value else EMPTY


def stored_day(text: str | None) -> str:
    """The day of a moment as the database keeps it, in ISO form."""
    return day(datetime.fromisoformat(text)) if text else EMPTY


def moment(value: datetime | None, seconds: bool = False) -> str:
    if value is None:
        return EMPTY
    clock = pattern("time") if seconds else pattern("short_time")
    return value.strftime(f"{pattern('date')} {clock}")


QT_FIELDS = {"%d": "dd", "%m": "MM", "%Y": "yyyy", "%H": "HH", "%M": "mm", "%S": "ss"}


def qt_moment() -> str:
    """Date and time with seconds as a Qt display format, for fields that edit a moment."""
    text = f"{pattern('date')} {pattern('time')}"
    for field, qt_field in QT_FIELDS.items():
        text = text.replace(field, qt_field)
    return text


def decimal(value: float, digits: int = 1) -> str:
    """A number with the decimal sign of the language."""
    return f"{value:.{digits}f}".replace(".", pattern("decimal"))
