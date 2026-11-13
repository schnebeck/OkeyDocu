# OkeyDocu - okeydocu/vocabulary/__init__.py
# The application's own words for what instruments measure, independent of any instrument.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Plans, templates, the store and the reports speak only in these keys.

A driver's mapping turns an instrument's codes into them; whatever it does not know
passes through as the instrument's code. Names are shown in the current language.
"""
from __future__ import annotations

import re
from functools import cache
from xml.sax.saxutils import escape

from ..l10n import in_language, tr
from .notation import conductors, is_marked, markup, plain
from .roles import ROLE_TEXT, Role, counts, role, stands_for
from .terms import Term, Vocabulary, VocabularyError, vocabulary

__all__ = ["ROLE_TEXT", "Role", "Term", "Vocabulary", "VocabularyError", "conductors", "counts",
           "function_keys", "function_label", "function_markup", "function_symbol", "markup",
           "outcome_text", "plain", "result_label", "result_markup", "result_name", "symbols_marked", "role", "setting_name",
           "stands_for", "units", "vocabulary"]

LABEL_SEPARATOR = " – "


def function_keys() -> list[str]:
    return list(vocabulary().functions)


def function_symbol(key: str) -> str:
    """What a function is called in short: its symbol, or its name if it has none."""
    term = vocabulary().functions.get(key)
    if term is None:
        return key
    return plain(tr(term.symbol)) if term.symbol else tr(term.name)


def function_label(key: str) -> str:
    """Symbol and name, such as `RLO – Protective conductor resistance`."""
    term = vocabulary().functions.get(key)
    if term is None:
        return key
    if not term.symbol:
        return tr(term.name)
    return plain(tr(term.symbol)) + LABEL_SEPARATOR + tr(term.name)


def function_markup(key: str, short: bool = False) -> str:
    """As `function_label`, with the symbol in italic and its index set low; `short` gives
    the symbol alone, as `function_symbol` does."""
    term = vocabulary().functions.get(key)
    if term is None:
        return escape(key)
    if not term.symbol:
        return escape(tr(term.name))
    if short:
        return markup(tr(term.symbol))
    return markup(tr(term.symbol)) + escape(LABEL_SEPARATOR + tr(term.name))


def result_label(key: str, stored: str = "") -> str:
    """A result's symbol; one the vocabulary does not know keeps what it was stored with."""
    term = vocabulary().results.get(key)
    if term is not None:
        return plain(tr(term.symbol)) if term.symbol else tr(term.name)
    return in_language(stored) if stored else key


def result_markup(key: str, stored: str = "") -> str:
    """As `result_label`, written as in mathematics."""
    term = vocabulary().results.get(key)
    if term is not None and term.symbol:
        return markup(tr(term.symbol))
    return escape(result_label(key, stored))


@cache
def _written_symbols() -> tuple[re.Pattern, dict[str, str]]:
    """Every symbol of the vocabulary as it appears in plain text, such as RLO or IΔN, with
    its markup. One letter alone is too common a word to be taken for a symbol."""
    found: dict[str, str] = {}
    terms = [*vocabulary().results.values(), *vocabulary().functions.values()]
    for word in (word for term in terms if term.symbol for word in term.symbol.split(" ")):
        if is_marked(word) and len(plain(word)) > 1:
            found.setdefault(plain(word), markup(word))
    tokens = sorted(found, key=len, reverse=True)
    pattern = re.compile(rf"(?<![\w])({'|'.join(map(re.escape, tokens))})(?![\w])")
    return pattern, found


def symbols_marked(text: str) -> str:
    """Plain text, such as an instrument's name of a setting, with the symbols in it set as in
    mathematics: `RLO - Polung` gets an italic R and a low LO."""
    pattern, found = _written_symbols()
    parts = pattern.split(text)
    return "".join(found[part] if index % 2 else escape(part) for index, part in enumerate(parts))


def result_name(key: str) -> str:
    term = vocabulary().results.get(key)
    return tr(term.name) if term is not None else ""


def outcome_text(word: str) -> str:
    """A neutral word such as `right` in the current language; anything else as it is."""
    term = vocabulary().outcomes.get(word)
    return tr(term.name) if term is not None else word


def setting_name(key: str) -> str | None:
    term = vocabulary().settings.get(key)
    return tr(term.name) if term is not None else None


def units() -> tuple[str, ...]:
    """Every unit of a quantity, longest first, so `Hz` is tried before a shorter one."""
    found = {term.unit for term in vocabulary().quantities.values() if term.unit}
    return tuple(sorted(found, key=len, reverse=True))
