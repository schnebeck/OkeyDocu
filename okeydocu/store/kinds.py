# OkeyDocu - okeydocu/store/kinds.py
# Kinds of structure elements, the features each can carry, and the values noted on an element.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

import yaml

from ..l10n import is_translation, tr

FALLBACK_ICON = "element"
_FOLDED = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


@dataclass(frozen=True)
class Feature:
    key: str
    label: str
    unit: str = ""
    choice_list: str | None = None  # key of the list of values offered; any other may be typed


@dataclass(frozen=True)
class Kind:
    key: str
    label: str
    icon: str = FALLBACK_ICON
    izytron_type: int | None = None
    interval_months: int = 0
    features: tuple[Feature, ...] = field(default_factory=tuple)


def slug(text: str) -> str:
    """A stable key from a label: lower case, ASCII, words joined by underscores."""
    folded = text.casefold().translate(_FOLDED)
    return re.sub(r"[^a-z0-9]+", "_", folded).strip("_") or "feature"


def _feature(spec, shared: dict[str, str]) -> Feature:
    """`Label|unit`, or a mapping with label, unit, a key of its own, which keeps values noted
    under an earlier label, and a list of its own. Otherwise the label names the list."""
    if isinstance(spec, dict):
        label = str(spec["label"])
        chosen = spec["list"] if "list" in spec else shared.get(label)
        return Feature(str(spec.get("key") or slug(label)), label, str(spec.get("unit", "")),
                       chosen)
    label, _, unit = spec.partition("|")
    return Feature(slug(label), label.strip(), unit.strip(), shared.get(label.strip()))


def shipped_kinds() -> list[Kind]:
    raw = yaml.safe_load(
        (resources.files("okeydocu") / "data" / "kinds.yaml").read_text(encoding="utf-8")
    )
    shared = {str(label): str(key) for label, key in (raw.get("lists") or {}).items()}

    def feature(spec) -> Feature:
        return _feature(spec, shared)

    return [
        Kind(item["key"], item["label"], item.get("icon", FALLBACK_ICON), item.get("izytron"),
             item.get("interval", 0), tuple(feature(spec) for spec in item.get("features", ())))
        for item in raw["kinds"]
    ]


@cache
def shipped_names() -> dict:
    """English names of the shipped kinds by key, of their features by (kind, feature) key."""
    names: dict = {}
    for kind in shipped_kinds():
        names[kind.key] = kind.label
        names.update({(kind.key, feature.key): feature.label for feature in kind.features})
    return names


def shown(shipped: str | None, label: str) -> str:
    """A stored label in the current language. A shipped name is recognised in every catalogued
    language by its key, so one word naming two things is no problem; a renamed one stays."""
    if shipped and is_translation(label, shipped):
        return tr(shipped)
    return label


class KindsMixin:
    """Kinds are shared by every customer, so changing one changes it everywhere."""

    def seed_kinds(self) -> None:
        for position, kind in enumerate(shipped_kinds()):
            self.save_kind(kind, position)

    def kinds(self) -> list[Kind]:
        """Labels in the current language, as far as they are the shipped ones."""
        rows = self.query("SELECT * FROM asset_kinds ORDER BY position, label COLLATE NOCASE")
        names = shipped_names()
        features: dict[str, list[Feature]] = {}
        for row in self.query("SELECT * FROM kind_features ORDER BY position, id"):
            label = shown(names.get((row["kind"], row["key"])), row["label"])
            features.setdefault(row["kind"], []).append(
                Feature(row["key"], label, row["unit"], row["choice_list"]))
        return [
            Kind(row["key"], shown(names.get(row["key"]), row["label"]), row["icon"],
                 row["izytron_type"], row["interval_months"],
                 tuple(features.get(row["key"], ())))
            for row in rows
        ]

    def kind(self, key: str) -> Kind | None:
        return next((kind for kind in self.kinds() if kind.key == key), None)

    def kind_labels(self) -> dict[str, str]:
        rows = self.query("SELECT key, label FROM asset_kinds")
        names = shipped_names()
        return {row["key"]: shown(names.get(row["key"]), row["label"]) for row in rows}

    def new_kind_key(self, label: str) -> str:
        base = slug(label)
        taken = {row["key"] for row in self.query("SELECT key FROM asset_kinds")}
        key, number = base, 2
        while key in taken:
            key, number = f"{base}_{number}", number + 1
        return key

    def save_kind(self, kind: Kind, position: int | None = None) -> None:
        """Insert or replace, features included. Values noted on elements stay untouched."""
        if position is None:
            row = self.one("SELECT position FROM asset_kinds WHERE key=?", kind.key)
            position = row["position"] if row else self._next_position()
        with self.transaction() as connection:
            connection.execute(
                "INSERT INTO asset_kinds (key, label, icon, izytron_type,"
                " interval_months, position) VALUES (?, ?, ?, ?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET label=excluded.label, icon=excluded.icon,"
                " izytron_type=excluded.izytron_type,"
                " interval_months=excluded.interval_months, position=excluded.position",
                (kind.key, kind.label, kind.icon, kind.izytron_type,
                 kind.interval_months, position),
            )
            connection.execute("DELETE FROM kind_features WHERE kind=?", (kind.key,))
            for number, feature in enumerate(kind.features):
                connection.execute(
                    "INSERT OR IGNORE INTO kind_features (kind, key, label, unit, position,"
                    " choice_list) VALUES (?, ?, ?, ?, ?, ?)",
                    (kind.key, feature.key, feature.label, feature.unit, number,
                     feature.choice_list),
                )

    def _next_position(self) -> int:
        row = self.one("SELECT max(position) AS last FROM asset_kinds")
        return (row["last"] or 0) + 1

    def kind_usage(self, key: str) -> int:
        return self.one("SELECT count(*) AS n FROM assets WHERE kind=?", key)["n"]

    def delete_kind(self, key: str, replacement: str | None = None) -> None:
        """Elements of the kind take `replacement`; without one, only an unused kind goes."""
        with self.transaction() as connection:
            if replacement is not None:
                connection.execute("UPDATE assets SET kind=? WHERE kind=?", (replacement, key))
            connection.execute("DELETE FROM asset_kinds WHERE key=?", (key,))

    # Values on an element -------------------------------------------------

    def asset_features(self, asset_id: int) -> dict[str, str]:
        row = self.one("SELECT features_json FROM assets WHERE id=?", asset_id)
        return json.loads(row["features_json"]) if row else {}

    def set_asset_features(self, asset_id: int, values: dict[str, str]) -> None:
        """Empty values are not kept: an empty feature is as good as none."""
        kept = {key: value.strip() for key, value in values.items() if value.strip()}
        self.execute(
            "UPDATE assets SET features_json=? WHERE id=?",
            json.dumps(kept, ensure_ascii=False, sort_keys=True), asset_id,
        )

    def set_asset_kind(self, asset_id: int, kind: str) -> None:
        self.execute("UPDATE assets SET kind=? WHERE id=?", kind, asset_id)

    def set_asset_interval(self, asset_id: int, months: int | None) -> None:
        self.execute("UPDATE assets SET interval_months=? WHERE id=?", months, asset_id)
