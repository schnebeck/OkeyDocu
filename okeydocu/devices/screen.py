# OkeyDocu - okeydocu/devices/screen.py
# What an instrument's display shows in a measuring function, as far as a guide needs it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A display with softkeys beside it is divided into as many rows as there are softkeys. The
row beside a key names what the key does; the rest of the row holds a reading, the measuring
path or a small line. A driver describes a view in the instrument's own short labels; the
application draws it in its own strokes."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Reading:
    label: str  # as the display names the quantity, such as "RLO"
    unit: str


@dataclass(frozen=True)
class Path:
    text: str  # what is measured between, such as "L1-PE"


@dataclass(frozen=True)
class Line:
    text: str  # a small line, such as voltage and frequency of the test point


@dataclass(frozen=True)
class Key:
    """What the row beside a softkey shows. A line may be divided into cells by "|"; a name in
    braces stands for what the element measured states under that feature."""

    lines: tuple[str, ...] = ()
    inverted: str = ""  # the line or cell shown inverted: the choice in force
    symbol: str = ""  # drawn in place of words: "share"


@dataclass(frozen=True)
class Screen:
    """One view. `rows` and `keys` run from the top, one entry per softkey; None is an empty
    row or a key without function. The first row is the header with the function's sign."""

    sign: str
    rows: tuple[Reading | Path | Line | None, ...]  # from the second row on
    keys: tuple[Key | None, ...]

    def with_key(self, index: int, key: Key | None) -> Screen:
        """The same view with another meaning for the softkey `index`, counted from 0."""
        keys = list(self.keys)
        keys[index] = key
        return replace(self, keys=tuple(keys))
