# OkeyDocu - okeydocu/campaign/plan_language.py
# The words of plans and instructions as read from YAML, told in the current language.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Shipped plans and instructions are written in English and translated by the catalogues;
plans a user wrote are in the user's language and stay as they are unless a catalogue knows
them. Keys, functions, sockets and terminal ids are never translated."""

from __future__ import annotations

from typing import Callable, Iterator

from ..l10n import in_language

TEXT_FIELDS = ("title", "selector", "source", "text", "dut", "question")
LIST_FIELDS = ("instructions", "warnings")


def _setting(item, change: Callable[[str], str]):
    """A setting as a plan file writes it, `{name: value}`, or as a stored step keeps it,
    `[name, value]`."""
    if isinstance(item, dict):
        return {change(str(key)): change(str(value)) for key, value in item.items()}
    key, value = item
    return [change(str(key)), change(str(value))]


def _changed(raw: dict, change: Callable[[str], str]) -> dict:
    data = dict(raw)
    for name in TEXT_FIELDS:
        if isinstance(data.get(name), str):
            data[name] = change(data[name])
    for name in LIST_FIELDS:
        if name in data:
            data[name] = [change(str(item)) for item in data[name] or ()]
    if "settings" in data:
        data["settings"] = [_setting(item, change) for item in data["settings"] or ()]
    wiring = data.get("wiring")
    if wiring:
        data["wiring"] = {
            **wiring,
            "object_label": change(wiring.get("object_label", "")),
            "terminals": [{**terminal, "label": change(terminal["label"])}
                          for terminal in wiring.get("terminals", ())],
        }
    return data


def told(raw: dict) -> dict:
    """A step, instruction or plan head with its words in the current language."""
    return _changed(raw, in_language)


def words(raw: dict) -> Iterator[str]:
    """Every text of a step, instruction or plan head that a catalogue may translate."""
    found: list[str] = []

    def collect(text: str) -> str:
        if text:
            found.append(text)
        return text

    _changed(raw, collect)
    return iter(found)
