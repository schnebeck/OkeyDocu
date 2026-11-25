# OkeyDocu - okeydocu/ui/place_station.py
# The first station of a guided measurement: the element measured, chosen or made on the way.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The tree names the element; the guide is taken at it or at the nearest one above that it
suits. Leaving the station stores what was entered at the element, making it first where it
is new, and the bench is drawn from it."""

from __future__ import annotations

from html import escape

from ..campaign.measuring_place import make_place, measuring_place, new_place
from ..l10n import tr
from .structure_tree import UNPLACED


class PlaceStation:
    """Mixed into the measuring window, which holds `app`, `base_guide`, `root` and
    `parent_id`. What the element states decides the run, so every preview plans it anew."""

    def show_place(self, asset_id: int | None) -> None:
        """The element readings go to, or a new one below `parent_id` where the guide finds
        none at `asset_id`; the tree shows which."""
        service = self.app.service
        found = measuring_place(service, self.base_guide, asset_id, self.root)
        if found.asset_id is None:
            found = new_place(service, self.base_guide, self.parent_id, self.root)
        self._take(found)
        # With nothing to measure at, the tree marks no element: any of them can be picked.
        marked = found.asset_id if found.asset_id is not None else self.parent_id
        self.form.select(marked if self.has_place else None)

    @property
    def has_place(self) -> bool:
        """An element readings can go to: one there is, or one about to be made."""
        return self.place.asset_id is not None or self.place.is_new

    def _take(self, place, typed: dict[str, str] | None = None) -> None:
        self.place = place
        self.form.show_place(self.base_guide, place, typed)
        self._preview()
        self._allow_next()

    def _choose(self, asset_id) -> None:
        """An element picked in the tree, or the tree worked on. Where the guide finds no
        element to be taken at, a new one will hang below the one picked. The element already
        shown keeps what was typed, and so does a new one that only hangs elsewhere."""
        asset_id = self.root if asset_id in (None, UNPLACED) else asset_id
        service = self.app.service
        found = measuring_place(service, self.base_guide, asset_id, self.root)
        if found.asset_id is None:
            if asset_id != self.parent_id:
                self.parent_id = asset_id
                self.parent_chosen.emit(asset_id)
            found = new_place(service, self.base_guide, asset_id, self.root)
        same = (found.asset_id, found.kind) == (self.place.asset_id, self.place.kind)
        self._take(found, self.form.entered() if same else None)

    def _shown(self):
        """The place as entered so far, a new one under a name of its own."""
        if not self.place.is_new:
            return self.place.entered(self.form.entered())
        return self.place.entered(self.form.entered(),
                                  tr("{title} (new)", title=self.form.title()))

    def _preview(self) -> None:
        shown = self.shown = self._shown()
        self._plan()
        self.scene.show_place(self.guide, shown)
        where = shown.title or tr("no element chosen")
        which = tr("repeat measurement") if self.repeat else tr("first measurement")
        self.head.setText(f"<b style='font-size:15pt'>{escape(tr(self.guide.title))}</b>"
                          f"&nbsp;&nbsp;<span style='color:gray'>"
                          f"{escape(tr('for {element}', element=where))}"
                          f" · {escape(which)}</span>")

    def _keep_place(self) -> None:
        if self.place.is_new:
            made = self.place.entered(self.form.entered())
            name = self.form.name.text().strip() or self.form.name.placeholderText()
            asset_id = make_place(self.app.service, made, self.parent_id, name,
                                  self.form.identifier.text().strip())
            self.show_place(asset_id)
            self.place_made.emit(asset_id)
        elif self.form.store():
            self.show_place(self.place.asset_id)
        if self.place.asset_id is not None:
            self.place_kept.emit(self.place.asset_id)
