# EasyMeasurement - easymeasurement/reporting/language.py
# The language a protocol is written in, independent of the language of the program.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every text a protocol shows is written in German and looked up by that text.

A catalogue in data/languages/<code>.yaml maps German to its language; what it
lacks stays German. Template texts may also be given per language, such as
`{de: Prüfprotokoll, en: Test report}`. While a protocol is generated, `speaking`
holds its language, so no function between template and PDF has to pass it on.
"""
from __future__ import annotations

import re
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime
from functools import cache
from importlib import resources

import yaml

SOURCE = "de"
_NAMES = {"de": "Deutsch", "en": "English"}
_current: ContextVar[str] = ContextVar("report_language", default=SOURCE)
_FORMATS = {"date": "%d.%m.%Y", "time": "%H:%M:%S", "short_time": "%H:%M", "decimal": ","}
_NUMBER = re.compile(r"^([<>≤≥]?)\s*(-?\d+(?:[.,]\d+)?)\s*(\S*)$")


def _folder():
    return resources.files("easymeasurement") / "data" / "languages"


@cache
def _data(code: str) -> dict:
    if code == SOURCE:
        return {}
    return yaml.safe_load((_folder() / f"{code}.yaml").read_text(encoding="utf-8")) or {}


@cache
def _catalogue(code: str) -> dict[str, str]:
    return {str(german): str(text) for german, text in (_data(code).get("texts") or {}).items()}


def _format(name: str) -> str:
    return (_data(_current.get()).get("formats") or {}).get(name, _FORMATS[name])


def languages() -> dict[str, str]:
    """Code and own name of every language a protocol can be written in."""
    found = {SOURCE: _NAMES[SOURCE]}
    for entry in sorted(_folder().iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".yaml"):
            code = entry.name.removesuffix(".yaml")
            data = yaml.safe_load(entry.read_text(encoding="utf-8")) or {}
            found[code] = data.get("name", _NAMES.get(code, code))
    return found


@contextmanager
def speaking(code: str):
    token = _current.set(code or SOURCE)
    try:
        yield
    finally:
        _current.reset(token)


def current() -> str:
    return _current.get()


@cache
def _structure(code: str, group: str) -> dict[str, str]:
    return {str(key): str(text) for key, text in (_data(code).get(group) or {}).items()}


def kind_name(key: str, german: str) -> str:
    """A kind of structure element by its key: one German word may name two kinds of thing."""
    return _structure(_current.get(), "kinds").get(key, german)


def feature_name(key: str, german: str) -> str:
    return _structure(_current.get(), "features").get(key, german)


def tr(text: str) -> str:
    return _catalogue(_current.get()).get(text, text)


def pick(value) -> str:
    """A template text, given once or per language."""
    if isinstance(value, dict):
        for code in (_current.get(), SOURCE):
            if value.get(code):
                return tr(str(value[code])) if code == SOURCE else str(value[code])
        return str(next(iter(value.values()), ""))
    return tr(str(value))


def day(value: date | None) -> str:
    return value.strftime(_format("date")) if value else "–"


def moment(value: datetime | None, seconds: bool = False) -> str:
    if value is None:
        return "–"
    clock = _format("time") if seconds else _format("short_time")
    return value.strftime(f"{_format('date')} {clock}")


UNIT_SPACE = "\u202f"  # narrow no-break space, between a number and its unit


def value_text(raw: str) -> str:
    """A reading as the instrument gave it, only with the decimal sign of the language and a
    narrow space that never breaks before the unit: `2.05MΩ` becomes `2,05 MΩ`. Digits,
    qualifier and unit stay as they are."""
    match = _NUMBER.match(raw.strip()) if raw else None
    if not match:
        return raw
    qualifier, number, unit = match.groups()
    number = number.replace(".", _format("decimal")).replace(",", _format("decimal"))
    return f"{qualifier}{number}" + (f"{UNIT_SPACE}{unit}" if unit else "")
