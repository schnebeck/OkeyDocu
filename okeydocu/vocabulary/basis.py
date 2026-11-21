# OkeyDocu - okeydocu/vocabulary/basis.py
# What a measuring function rests on: standards, why it is taken, where to measure next.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The basis belongs to the function, not to an instrument: every driver's guide for a function
shows the same. Standards are codes and clause numbers and read the same in every language;
`why` and `further` are English and translated by the catalogues."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib import resources

import yaml


@dataclass(frozen=True)
class Basis:
    standards: tuple[str, ...]
    why: str
    further: str


@cache
def bases() -> dict[str, Basis]:
    path = resources.files("okeydocu") / "data" / "basis.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {function: Basis(tuple(entry.get("standards") or ()), entry.get("why", ""),
                            entry.get("further", ""))
            for function, entry in (raw.get("functions") or {}).items()}


def basis_of(function: str) -> Basis | None:
    return bases().get(function)


def basis_texts() -> set[str]:
    """Every text of the bases that is told in a language."""
    return {text for basis in bases().values() for text in (basis.why, basis.further) if text}
