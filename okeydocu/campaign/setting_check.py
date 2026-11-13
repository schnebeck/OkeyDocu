# OkeyDocu - okeydocu/campaign/setting_check.py
# The settings an instrument was used with, held against the element they were set for.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The settings of an RCD test describe the RCD it tests: the nearest element at or above the
measured one whose kind has an RCD type. Each setting keyed like a feature of that element is
compared with it. An RCD test without such an element, or at one that does not state a
setting, is a finding of its own: nothing could be compared. Numbers are compared in base
units, so 30 mA on the instrument meets 30 at a feature counted in mA; words without spaces,
dashes and a leading `Typ`, so `Typ B` meets `B` and `A - EV` meets `A-EV` but not `A`. A
value that is not known or cannot be read, on either side, is not compared: the check never
claims what it cannot tell."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

from ..devices.registry import setting_words
from ..l10n import tr
from ..model import Quantity
from ..vocabulary import setting_name

OWNER = "rcd_type"  # the feature that marks the kind of element the compared settings describe
COMPARED = ("rcd_type", "rated_residual_current", "rated_current")
RCD_FUNCTIONS = frozenset({"rcd_time", "rcd_touch", "rcd_current", "rcd_ramp_touch", "i_ramp"})


@dataclass(frozen=True)
class Mismatch:
    key: str
    used: str  # as the instrument was set, in words
    expected: str  # as the element states it, with its unit
    element: str  # the element's designation

    def text(self) -> str:
        return tr("{setting}: {used} on the instrument, {expected} at {element}",
                  setting=setting_name(self.key) or self.key, used=self.used,
                  expected=self.expected, element=self.element)


@dataclass(frozen=True)
class NoRcd:
    """An RCD test booked where no RCD is at or above."""

    def text(self) -> str:
        return tr("Not booked on an RCD: the settings cannot be checked. Book the reading on"
                  " the RCD it tests.")


@dataclass(frozen=True)
class Unstated:
    keys: tuple[str, ...]
    element: str

    def text(self) -> str:
        names = ", ".join(setting_name(key) or key for key in self.keys)
        return tr("{element} does not state {settings}: not checked. Enter it at the element.",
                  element=self.element, settings=names)


def _number(text: str) -> float | None:
    quantity = Quantity.parse(text)
    return quantity.base_value if quantity is not None else None


_SPACING = re.compile(r"[\s\-_]+")
_TYPE = re.compile(r"^(TYPE|TYP)(?=.)")


def _word(text: str) -> str:
    """Upper case without spaces, dashes and a leading `Type`: `Typ A - EV` reads `AEV`."""
    return _TYPE.sub("", _SPACING.sub("", text.upper()))


def same(used: str, expected: str) -> bool | None:
    """Whether a setting matches the element; None where the two cannot be compared."""
    numbers = _number(used), _number(expected)
    if None not in numbers:
        return math.isclose(*numbers, rel_tol=1e-6)
    if numbers != (None, None):
        return None
    used, expected = _word(used), _word(expected)
    return used == expected if used and expected else None


class SettingCheck:
    """For one screen: elements and the instrument's words are read once, on first need."""

    def __init__(self, db):
        self.db = db
        self._words = None
        self._owners: dict[int, object] = {}
        units = db.query("SELECT kind, key, unit FROM kind_features")
        self._units = {(row["kind"], row["key"]): row["unit"] for row in units}
        self._rcd_kinds = {kind for kind, key in self._units if key == OWNER}

    def owner(self, asset_id: int | None):
        """The element at or above `asset_id` whose settings are compared, or None."""
        if asset_id is None:
            return None
        if asset_id not in self._owners:
            found, current, seen = None, asset_id, set()
            while current is not None and current not in seen:
                seen.add(current)
                row = self.db.one("SELECT * FROM assets WHERE id=?", current)
                if row is None:
                    break
                if row["kind"] in self._rcd_kinds:
                    found = row
                    break
                current = row["parent_id"]
            self._owners[asset_id] = found
        return self._owners[asset_id]

    def element(self, asset_id: int | None) -> str:
        """The designation of the element whose settings are compared, or nothing."""
        row = self.owner(asset_id)
        return (row["identifier"] or row["name"]) if row is not None else ""

    def expected(self, asset_id: int | None) -> list[tuple[str, str]]:
        """What the instrument should be set to for `asset_id`: each compared setting the
        element states, with its unit."""
        row = self.owner(asset_id)
        if row is None:
            return []
        features = json.loads(row["features_json"] or "{}")
        found = []
        for key in COMPARED:
            value = str(features.get(key) or "").strip()
            if value:
                unit = self._units.get((row["kind"], key), "")
                found.append((key, f"{value} {unit}".strip()))
        return found

    def _word(self, value: str) -> tuple[str, bool]:
        """The value in words, and whether it could be put in words at all."""
        if self._words is None:
            self._words = setting_words(self.db)
        return self._words.word(value)

    def findings(self, function: str, parameters: list[tuple[str, str]],
                 asset_id: int | None) -> list:
        """What keeps an RCD test from matching the RCD it was booked on; other tests are not
        judged."""
        if function not in RCD_FUNCTIONS:
            return []
        if self.owner(asset_id) is None:
            return [NoRcd()]
        expected = dict(self.expected(asset_id))
        element = self.element(asset_id)
        found: list = []
        unstated = tuple(key for key in COMPARED if key not in expected)
        if unstated:
            found.append(Unstated(unstated, element))
        for key, value in parameters:
            if key in expected:
                used, said = self._word(value)
                if said and same(used, expected[key]) is False:
                    found.append(Mismatch(key, used, expected[key], element))
        return found

    def of_row(self, row) -> list:
        """For a stored measurement."""
        stored = json.loads(row["parameters_json"] or "[]")
        parameters = [(item["key"], item["value"]) for item in stored]
        return self.findings(row["function"], parameters, row["asset_id"])
