# OkeyDocu - okeydocu/store/choice_lists.py
# Choice lists: the values a feature offers, each with its facts, help, curve and methods.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A choice list is a small table: its values are the rows, its attributes the columns and a
fact one cell. A value may carry a few paragraphs of help, a time-current characteristic, a
picture and the measuring functions suited to an element that holds it. A new database
starts with the lists of data/choice_lists.yaml; from then on they are the user's.

Shipped texts are stored in English and told in the current language by the catalogues."""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources

import yaml


@dataclass(frozen=True)
class Method:
    function: str  # a measuring function of the vocabulary
    note: str = ""


@dataclass(frozen=True)
class ChoiceValue:
    value: str
    facts: dict[str, str] = field(default_factory=dict)
    help: str = ""
    curve: str = ""
    picture: bytes = b""
    methods: tuple[Method, ...] = ()


@dataclass(frozen=True)
class ChoiceList:
    key: str
    label: str
    help: str = ""
    attributes: tuple[str, ...] = ()
    values: tuple[ChoiceValue, ...] = ()

    @property
    def offered(self) -> tuple[str, ...]:
        return tuple(entry.value for entry in self.values)

    def entry(self, value: str) -> ChoiceValue | None:
        return next((entry for entry in self.values if entry.value == value), None)

    def telling(self) -> tuple[str, ...]:
        """The attributes in which the values differ; what all of them share tells nothing
        about one of them. A list of one value tells everything."""
        if len(self.values) < 2:
            return self.attributes
        return tuple(name for name in self.attributes
                     if len({entry.facts.get(name, "") for entry in self.values}) > 1)


def _value(value, spec) -> ChoiceValue:
    spec = spec or {}
    methods = tuple(Method(str(item["function"]), str(item.get("note", "")))
                    for item in spec.get("methods") or ())
    return ChoiceValue(str(value), {str(k): str(v) for k, v in (spec.get("facts") or {}).items()},
                       str(spec.get("help", "")).strip(), str(spec.get("curve", "")), b"",
                       methods)


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def shipped_choice_lists() -> list[ChoiceList]:
    entry = resources.files("okeydocu") / "data" / "choice_lists.yaml"
    raw = yaml.safe_load(entry.read_text(encoding="utf-8")) or {}
    found = []
    for key, spec in (raw.get("lists") or {}).items():
        values = spec.get("values") or {}
        if isinstance(values, list):
            values = {value: None for value in values}
        found.append(ChoiceList(str(key), str(spec["label"]), str(spec.get("help", "")).strip(),
                                tuple(str(name) for name in spec.get("attributes") or ()),
                                tuple(_value(value, facts) for value, facts in values.items())))
    return found


def shipped_choice_texts() -> set[str]:
    """Every text of the shipped lists that is told in a language: labels, attributes, facts,
    help and the notes of methods. Values are told where they are not numbers, which take the
    decimal sign of the language instead."""
    found = set()
    for shipped in shipped_choice_lists():
        found |= {shipped.label, *shipped.attributes} | ({shipped.help} - {""})
        for entry in shipped.values:
            found |= set(entry.facts.values()) | ({entry.help} - {""})
            found |= set() if _is_number(entry.value) else {entry.value}
            found |= {method.note for method in entry.methods if method.note}
    return found
