# EasyMeasurement - easymeasurement/ui/choice_tips.py
# What a value of a choice list tells in its tooltip: facts, help, curve, picture, methods.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The facts told are those in which the values of the list differ. A curve is drawn for the
element at hand: its rated current turns multiples into amperes, and its earthing system with
the rated current gives the disconnection time required (DIN VDE 0100-410, table 41.1, at
U₀ 230 V). The table holds for final circuits with socket-outlets up to 63 A and for fixed
equipment up to 32 A; whether a circuit feeds socket-outlets is not known here, so up to 63 A
the shorter time is taken."""
from __future__ import annotations

from collections.abc import Callable, Mapping

from PySide6.QtGui import QPixmap

from ..l10n import in_language, tr
from ..store.choice_lists import ChoiceList, ChoiceValue
from ..vocabulary import function_label
from .curve_picture import curve_picture, parse_curve
from .rich_tip import Tip

Context = Callable[[], Mapping[str, str]]  # feature key → text of the element at hand
RATED = "rated_current"
EARTHING = "earthing_system_type"
FINAL_LIMIT_A = 63
REQUIRED_S = {("TN", True): 0.4, ("TN", False): 5.0, ("TT", True): 0.2, ("TT", False): 1.0}


def _number(text: str) -> float | None:
    try:
        return float(text.replace(",", ".").strip())
    except ValueError:
        return None


def required_time(context: Mapping[str, str]) -> float:
    """TN where the system is not told, a final circuit where the rated current is not."""
    rated = _number(context.get(RATED, ""))
    system = "TT" if context.get(EARTHING, "").strip().upper().startswith("TT") else "TN"
    return REQUIRED_S[(system, rated is None or rated <= FINAL_LIMIT_A)]


def pictures(entry: ChoiceValue, context: Mapping[str, str]) -> tuple[QPixmap, ...]:
    found = []
    breaker = parse_curve(entry.curve)
    if breaker is not None:
        found.append(curve_picture(breaker, required_time(context),
                                   _number(context.get(RATED, ""))))
    if entry.picture:
        own = QPixmap()
        if own.loadFromData(entry.picture):
            found.append(own)
    return tuple(found)


def value_tip(chosen: ChoiceList, entry: ChoiceValue, shown: str,
              context: Mapping[str, str] | None = None) -> Tip:
    rows = tuple((in_language(name), in_language(entry.facts[name]))
                 for name in chosen.telling() if entry.facts.get(name))
    lines = tuple(function_label(method.function)
                  + (f": {in_language(method.note)}" if method.note else "")
                  for method in entry.methods)
    if lines:
        lines = (tr("Suited measurements:"), *lines)
    title = f"{in_language(chosen.label)}: {shown}" if chosen.label else shown
    return Tip(title, rows, in_language(entry.help), pictures(entry, context or {}), lines)


def list_tip(chosen: ChoiceList) -> Tip | None:
    """What the list as a whole is about, told while no value of it is chosen."""
    if not chosen.help:
        return None
    return Tip(in_language(chosen.label), text=in_language(chosen.help))
