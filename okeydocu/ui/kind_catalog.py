# OkeyDocu - okeydocu/ui/kind_catalog.py
# Names and pictures of the kinds of structure elements, as the screen shows them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from importlib import resources

from PySide6.QtGui import QIcon

from ..l10n import tr
from ..store.kinds import FALLBACK_ICON, Kind, shipped_kinds

CUSTOMER_ICON, UNPLACED_ICON = "customer", "unplaced"
_FOLDER = resources.files("okeydocu") / "data" / "icons"
_ICONS: dict[str, QIcon] = {}
_ICON_TEXT: dict[str, str] = {}


def element_icon(name: str) -> QIcon:
    """The shipped picture of that name, or the neutral one for a name that is gone."""
    if name not in _ICONS:
        path = _FOLDER / f"{name}.svg"
        if not path.is_file():
            return element_icon(FALLBACK_ICON) if name != FALLBACK_ICON else QIcon()
        _ICONS[name] = QIcon(str(path))
    return _ICONS[name]


def icon_text(name: str) -> str:
    """A name for a picture: the shipped kind that uses it, or a description."""
    if not _ICON_TEXT:
        _ICON_TEXT.update({kind.icon: tr(kind.label) for kind in shipped_kinds()})
        _ICON_TEXT.update(building=tr("Building"), room=tr("Room"), element=tr("General"))
    return _ICON_TEXT.get(name, name.replace("_", " "))


def icon_names() -> list[str]:
    """What a kind can look like; the customer and the "no place" pictures are taken."""
    names = sorted(entry.name[:-4] for entry in _FOLDER.iterdir() if entry.name.endswith(".svg"))
    return [name for name in names if name not in (CUSTOMER_ICON, UNPLACED_ICON)]


class KindCatalog:
    """A snapshot of the kinds; build a new one after they changed."""

    def __init__(self, db):
        self.db = db
        self.all: list[Kind] = db.kinds()
        self.by_key = {kind.key: kind for kind in self.all}

    def label(self, key: str) -> str:
        kind = self.by_key.get(key)
        return kind.label if kind else key

    def icon(self, key: str) -> QIcon:
        kind = self.by_key.get(key)
        return element_icon(kind.icon if kind else FALLBACK_ICON)

    def most_used(self, count: int = 8) -> list[Kind]:
        """The kinds this database uses most, for the short list of a menu."""
        rows = self.db.query(
            "SELECT kind, count(*) AS n FROM assets GROUP BY kind ORDER BY n DESC LIMIT ?", count
        )
        used = [self.by_key[row["kind"]] for row in rows if row["kind"] in self.by_key]
        for kind in self.all:
            if len(used) >= count:
                break
            if kind not in used:
                used.append(kind)
        return used
