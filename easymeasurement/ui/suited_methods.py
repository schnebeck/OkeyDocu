# EasyMeasurement - easymeasurement/ui/suited_methods.py
# The measurements suited to an element, gathered from the values its features hold.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every value of a choice list may name measuring functions suited to an element holding it.
An element's features together name a set of them; each function keeps the values that
named it, with their notes, which its tip shows.

What the tips of an element draw also depends on where it sits: the earthing system is
usually told on the machine or the supply above it, so the nearest element above that tells
one gives it to all below that do not."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..l10n import in_language
from ..store.choice_lists import ChoiceList
from ..vocabulary import function_label
from .choice_tips import EARTHING, choice_text, held_value
from .rich_tip import Tip

INHERITED = (EARTHING,)
DEPTH_LIMIT = 64  # deeper than any structure; ends the walk on a broken parent chain

Reason = tuple[str, str]  # (feature: value, note)


def suited(features: Iterable, lists: Mapping[str, ChoiceList],
           values: Mapping[str, str]) -> dict[str, list[Reason]]:
    """Function key → the values that name it, in the order of the features."""
    found: dict[str, list[Reason]] = {}
    for feature in features:
        chosen = lists.get(feature.choice_list or "")
        text = values.get(feature.key, "")
        value = held_value(chosen, text) if chosen is not None and text else None
        entry = chosen.entry(value) if value is not None else None
        for method in entry.methods if entry else ():
            reason = (f"{feature.label}: {choice_text(value)}",
                      in_language(method.note))
            found.setdefault(method.function, []).append(reason)
    return found


def method_tip(function: str, reasons: list[Reason]) -> Tip:
    return Tip(function_label(function), tuple(reasons))


def context_of(db, asset_id: int | None, own: Mapping[str, str]) -> dict[str, str]:
    """The element's own values, with those of `INHERITED` it lacks from above."""
    context = {key: text for key, text in own.items() if text.strip()}
    missing = [key for key in INHERITED if key not in context]
    row = db.asset(asset_id) if asset_id is not None else None
    for _ in range(DEPTH_LIMIT):
        if not missing or row is None or row["parent_id"] is None:
            break
        row = db.asset(row["parent_id"])
        if row is None:
            break
        above = db.asset_features(row["id"])
        for key in [key for key in missing if above.get(key, "").strip()]:
            context[key] = above[key]
            missing.remove(key)
    return context
