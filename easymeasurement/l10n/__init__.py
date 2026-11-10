# EasyMeasurement - easymeasurement/l10n/__init__.py
# Translating the program's texts, written in English, into the chosen language.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every text is written in English and looked up by that text when it is shown.

    tr("Serial number {serial}", serial=identity.serial)
    plural(count, "{count} photo", "{count} photos")

A text given to a module-level constant is marked with `N_` and translated where
it is shown, because modules load before the language is chosen. The program's
language is set once at start. `speaking` sets another one for the work of the
current thread, such as a protocol written in a language of its own.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from .catalog import SOURCE, Catalog, available, catalog, source_of
from .formats import day, decimal, moment, qt_moment

__all__ = ["SOURCE", "N_", "available", "current", "day", "decimal", "in_language",
           "is_translation", "moment", "plural", "qt_moment", "set_language", "speaking",
           "tr"]

_chosen = SOURCE
_speaking: ContextVar[str | None] = ContextVar("speaking", default=None)


def N_(text: str) -> str:  # noqa: N802 - the usual marker name for a text translated later
    """Marks a text for the catalogue without translating it yet."""
    return text


def set_language(code: str) -> None:
    """The program's language; an unknown one falls back to English."""
    global _chosen
    _chosen = code if code in available(program=True) else SOURCE


def current() -> str:
    return _speaking.get() or _chosen


def active() -> Catalog:
    return catalog(current())


@contextmanager
def speaking(code: str):
    token = _speaking.set(code or SOURCE)
    try:
        yield
    finally:
        _speaking.reset(token)


def tr(text: str, /, context: str = "", **values) -> str:
    translated = active().text(text, context) or text
    return translated.format(**values) if values else translated


def in_language(text: str) -> str:
    """A stored text, such as a step title or a template line, that may have been written in
    any language with a catalogue: told in the current language if it is known, else as it is."""
    if not text:
        return text
    found = active().text(text)
    if found is not None:
        return found
    source = source_of(text)
    if source is None:
        return text
    return active().text(source) or source


def is_translation(text: str, source: str) -> bool:
    """Whether `text` is `source` itself or its translation into a catalogued language."""
    return text == source or any(catalog(code).text(source) == text for code in available())


def plural(count: int, one: str, many: str, /, context: str = "", **values) -> str:
    """`count` fills `{count}` in either text."""
    return tr(one if count == 1 else many, context, count=count, **values)
