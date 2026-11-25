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
application draws it in its own strokes. A reading and a line name the values of a result
they show, by the keys of the vocabulary: once a result stands, they carry its values in
place of their dashes.

A softkey of a setting opens a second kind of view, the setting list: what can be chosen for
each setting of that softkey, worded as the instrument words it."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Reading:
    label: str  # as the display names the quantity, such as "RLO"
    unit: str
    values: tuple[str, ...] = ()  # keys of the value shown here; the first a result has


@dataclass(frozen=True)
class Path:
    text: str  # what is measured between, such as "L1-PE"


@dataclass(frozen=True)
class Line:
    text: str  # a small line, such as voltage and frequency of the test point
    values: tuple[str, ...] = ()  # keys of the values that take the place of its dashes, in order


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

    def softkey(self, key: Key) -> int | None:
        """Which softkey, counted from 0, has `key` in its row; None where the view lacks it."""
        return self.keys.index(key) if key in self.keys else None

    def with_key(self, index: int, key: Key | None) -> Screen:
        """The same view with another meaning for the softkey `index`, counted from 0."""
        keys = list(self.keys)
        keys[index] = key
        return replace(self, keys=tuple(keys))


@dataclass(frozen=True)
class Setting:
    """One setting as a setting list names it with its value, and what can be chosen for it.
    `pages` are the choices as the instrument turns them over, each as it words it; `of` says
    how many pages the instrument has where not all of them are known; `typed` is a value
    entered by hand, offered last; `feature` what the element states that names the choice."""

    shown: str  # may hold a name in braces, as a softkey row does
    pages: tuple[tuple[str, ...], ...] = ()
    typed: str = ""
    feature: str = ""
    of: int = 0

    def page_count(self) -> int:
        return max(self.of, len(self.pages), 1)

    def offered(self) -> tuple[tuple[str, ...], ...]:
        """Every row the cursor can stand on, page by page: the choices, and behind the last
        of them the value entered by hand."""
        pages = self.pages or ((),)
        return (*pages[:-1], (*pages[-1], *((self.typed,) if self.typed else ())))

    def worded(self, choice: str) -> str:
        """How the list names the setting once `choice` is taken: a choice words itself, a
        value entered by hand follows the name the setting carries."""
        if choice != self.typed or any(choice in page for page in self.pages):
            return choice
        name = self.shown[:min((self.shown.find(sign) for sign in "<>" if sign in self.shown),
                               default=0)]
        return name + choice


# What the softkeys do in a setting list, top down: with the cursor on the settings, and with
# it on the choices, where the third one confirms.
LIST_KEYS = ("up", "down", "right", "take")
CHOICE_KEYS = ("up", "down", "enter", "take")


@dataclass(frozen=True)
class SettingList:
    """The view a softkey of a setting opens: the settings of that softkey in a column on the
    left, the one selected framed, and its choices in a column on the right. `cursor` is the
    page and row of the choice the cursor stands on once it has passed to the right column;
    `taken` what has been confirmed there, by setting."""

    settings: tuple[Setting, ...]
    selected: int = 0
    cursor: tuple[int, int] | None = None
    taken: tuple[tuple[int, str], ...] = ()

    def at(self, index: int) -> SettingList:
        """The same list with another setting selected and the cursor on the settings."""
        return replace(self, selected=index, cursor=None)

    def keys(self) -> tuple[str, ...]:
        return LIST_KEYS if self.cursor is None else CHOICE_KEYS

    def wording(self, index: int) -> str:
        """How the setting `index` reads: as confirmed, or as the list opens with it."""
        return dict(self.taken).get(index, self.settings[index].shown)

    def moved(self, step: int) -> SettingList:
        """The cursor one row up or down: among the settings, or among the choices, where it
        turns the page at either end. It stops at the first and the last row."""
        if self.cursor is None:
            index = min(max(self.selected + step, 0), len(self.settings) - 1)
            return replace(self, selected=index)
        pages = self.settings[self.selected].offered()
        spots = [(page, row) for page, rows in enumerate(pages) for row in range(len(rows))]
        if not spots:
            return self
        here = spots.index(self.cursor) if self.cursor in spots else 0
        return replace(self, cursor=spots[min(max(here + step, 0), len(spots) - 1)])

    def across(self, start: tuple[int, int] = (0, 0)) -> SettingList:
        """From the settings to the choices of the one selected, the cursor on `start`."""
        pages = self.settings[self.selected].offered()
        known = start[0] < len(pages) and start[1] < len(pages[start[0]])
        return replace(self, cursor=start if known else (0, 0)) if any(pages) else self

    def confirmed(self) -> SettingList:
        """The choice under the cursor taken for its setting, the cursor back on the settings."""
        if self.cursor is None:
            return self
        page, row = self.cursor
        setting = self.settings[self.selected]
        choice = setting.offered()[page][row]
        taken = {**dict(self.taken), self.selected: setting.worded(choice)}
        return replace(self, cursor=None, taken=tuple(sorted(taken.items())))
