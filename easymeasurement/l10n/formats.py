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


def _format(name: str) -> str:
    from . import active

    return active().formats.get(name, DEFAULTS[name])


def day(value: date | None) -> str:
    return value.strftime(_format("date")) if value else EMPTY


def moment(value: datetime | None, seconds: bool = False) -> str:
    if value is None:
        return EMPTY
    clock = _format("time") if seconds else _format("short_time")
    return value.strftime(f"{_format('date')} {clock}")


def decimal(value: float, digits: int = 1) -> str:
    """A number with the decimal sign of the language."""
    return f"{value:.{digits}f}".replace(".", _format("decimal"))
