# EasyMeasurement - easymeasurement/vocabulary/terms.py
# The words of the application's vocabulary and the domain files they are read from.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every file in data/vocabulary/ adds the words of one field of measurement.

Two files may not define the same key twice, so a new field can never change the
meaning of a key that measurements are already stored with.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import cache
from importlib import resources

import yaml

GROUPS = ("quantities", "results", "functions", "outcomes", "settings")


class VocabularyError(ValueError):
    pass


@dataclass(frozen=True)
class Term:
    """A key with its English name and, where it has one, its symbol."""

    key: str
    name: str
    symbol: str = ""
    unit: str = ""  # quantities only
    quantity: str = ""  # results only
    results: tuple[str, ...] = ()  # functions only, optional


@dataclass(frozen=True)
class Vocabulary:
    quantities: dict[str, Term] = field(default_factory=dict)
    results: dict[str, Term] = field(default_factory=dict)
    functions: dict[str, Term] = field(default_factory=dict)
    outcomes: dict[str, Term] = field(default_factory=dict)
    settings: dict[str, Term] = field(default_factory=dict)


def folder():
    return resources.files("easymeasurement") / "data" / "vocabulary"


FIELDS = {"name", "symbol", "unit", "quantity", "results"}


def _term(key, spec: dict) -> Term:
    unknown = set(spec) - FIELDS
    if unknown:  # a comma in an unquoted name splits it into a field of its own
        raise VocabularyError(f"{key}: unknown fields {sorted(unknown)}")
    return Term(str(key), str(spec.get("name", key)), str(spec.get("symbol", "")),
                str(spec.get("unit", "")), str(spec.get("quantity", "")),
                tuple(str(result) for result in spec.get("results", ())))


@cache
def vocabulary() -> Vocabulary:
    found = Vocabulary()
    for entry in sorted(folder().iterdir(), key=lambda e: e.name):
        if not entry.name.endswith(".yaml"):
            continue
        data = yaml.safe_load(entry.read_text(encoding="utf-8")) or {}
        for group in GROUPS:
            target = getattr(found, group)
            for key, spec in (data.get(group) or {}).items():
                if str(key) in target:
                    raise VocabularyError(f"{entry.name}: {group} {key!r} is defined twice")
                target[str(key)] = _term(key, spec or {})
    return found
