# OkeyDocu - okeydocu/ui/place_station.py
# The first station of a guided measurement: the element measured, chosen or made on the way.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Leaving the station stores what was entered at the element, making it first where it is
new, and the bench is drawn from it."""

from __future__ import annotations

from dataclasses import replace
from html import escape

from ..campaign.measuring_place import candidates, make_place, measuring_place, new_place, \
    places
from ..l10n import tr
from .place_form import NEW


class PlaceStation:
    """Mixed into the measuring window, which holds `app`, `guide`, `root` and `parent_id`."""

    def show_place(self, asset_id: int | None) -> None:
        service = self.app.service
        found = None if asset_id == NEW else measuring_place(service, self.guide, asset_id,
                                                              self.root)
        if found is None or found.asset_id is None:
            found = new_place(service, self.guide, self.parent_id, self.root)
        self.place = found
        self.form.show_place(self.guide, self.place, candidates(service, self.guide, self.root),
                             places(service, self.root), self.parent_id)
        self._preview()

    def _hang_below(self, parent_id: int) -> None:
        """A new element hangs below another one; what was entered stays."""
        self.parent_id = parent_id
        moved = new_place(self.app.service, self.guide, parent_id, self.root)
        self.place = moved.entered(self.place.features)
        self._preview()
        self.parent_chosen.emit(parent_id)

    def _shown(self):
        """The place as entered so far, a new one under a name of its own."""
        if not self.place.is_new:
            return self.place.entered(self.form.entered())
        return self.place.entered(self.form.entered(),
                                  tr("{title} (new)", title=self.form.title()))

    def _preview(self) -> None:
        shown = self._shown()
        # Without N at the test point the N lead stays where it is.
        leads = tuple(lead for lead in self.base_guide.leads
                      if not (shown.has_n is False and lead.probe.startswith("N")))
        self.guide = replace(self.base_guide, leads=leads)
        self.scene.show_place(self.guide, shown)
        self.bench.show_guide(self.guide, shown.lines(self.guide.drawing_features),
                              shown.poles, shown.n_left)
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
