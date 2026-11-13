# OkeyDocu - okeydocu/ui/campaign_places.py
# Choosing an element of the structure narrows the table and decides where new readings go.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..campaign.setting_check import SettingCheck
from .element_form import ElementOverlay
from .structure_tree import UNPLACED


class CampaignPlaces:
    """Each campaign remembers its chosen element, so a reading lands where the tester is."""

    def _place_chosen(self, asset_id) -> None:
        if self.campaign_id is None:
            return
        if asset_id == UNPLACED:
            self.values.show_unplaced()
            self.place.show_element(None, None, False)
            return
        self.place_targets[self.campaign_id] = asset_id
        self.values.show_point(asset_id)
        self._show_place(asset_id)

    def _show_place(self, asset_id: int | None) -> None:
        campaign = self._campaign()
        if campaign is None:
            self.place.show_element(None, None, False)
            self._show_settings_for(None)
            return
        self.place.show_element(asset_id or campaign["asset_id"], campaign["id"],
                                campaign["status"] == "open")
        self._show_settings_for(asset_id or campaign["asset_id"])

    def _show_settings_for(self, asset_id: int | None) -> None:
        """The instructions name what the element that readings go to states for them."""
        check = SettingCheck(self.app.db)
        expected = check.expected(asset_id)
        element = check.element(asset_id) if check.owner(asset_id) is not None else None
        self.guided.show_element(expected, element)
        self.free.instruction.show_element(expected, element)

    def place_target(self, campaign_id: int) -> int:
        """Where a reading for that campaign is booked: the chosen element, or the whole."""
        chosen = self.place_targets.get(campaign_id)
        return chosen if chosen is not None else self.app.service.campaign(campaign_id)["asset_id"]

    def _refresh_structure(self) -> None:
        campaign = self._campaign()
        if campaign is not None:
            self.structure.show_root(campaign["asset_id"], campaign["id"],
                                     campaign["status"] == "open")
            self._show_place(self.place_targets.get(campaign["id"]))

    def _edit_element(self, asset_id: int | None) -> None:
        campaign = self._campaign()
        if campaign is None:
            return
        ElementOverlay(self.app, asset_id or campaign["asset_id"], self).exec()
        self._refresh_structure()
        self.values.refresh()
        self.list.update_campaign(campaign["id"])
        self.changed.emit()
