# OkeyDocu - okeydocu/ui/campaign_guide.py
# A guided measurement opened from a campaign: where its readings go, what it is told.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The window stays open beside the campaign, which keeps receiving. The element kept at the
first station becomes where the campaign's readings go, so the result of the last station
lands there. Where new elements hang is kept per campaign until it is changed."""

from __future__ import annotations

from shiboken6 import isValid

from .measuring_window import MeasuringWindow


class CampaignGuide:
    """Mixed into the campaign page."""

    guide_window: MeasuringWindow | None = None
    position = None  # where the switch stood when the instrument was asked last
    new_parents: dict[int, int] | None = None  # campaign to where new elements hang

    def open_guide(self, function: str) -> None:
        campaign = self._campaign()
        if campaign is None:
            return
        self.close_guide()
        if self.new_parents is None:
            self.new_parents = {}
        campaign_id = campaign["id"]
        window = MeasuringWindow(self.app, campaign_id, campaign["driver"], function,
                                 self.place_targets.get(campaign_id),
                                 self.new_parents.get(campaign_id), self.window(),
                                 repeat=not self.free.starter.is_first(function))
        window.place_kept.connect(lambda asset_id: self._guide_place(campaign_id, asset_id))
        window.parent_chosen.connect(
            lambda parent_id: self.new_parents.__setitem__(campaign_id, parent_id))
        window.selector_wanted.connect(self._guide_asks_selector)
        window.finished.connect(lambda _: self._guide_closed(window))
        self.guide_window = window
        window.show()
        if self.position is not None:
            window.show_selector(self.position)

    def _guide_place(self, campaign_id: int, asset_id: int) -> None:
        self.place_targets[campaign_id] = asset_id
        if campaign_id == self.campaign_id:
            self._refresh_structure()
            self.structure.select(asset_id)
            self.values.show_point(asset_id)

    def _guide_asks_selector(self) -> None:
        if self.session is not None and self.live_id == self.campaign_id:
            self.session.read_selector()

    def _guide_closed(self, window: MeasuringWindow) -> None:
        if self.guide_window is window:
            self.guide_window = None
        window.deleteLater()
        self._update()

    def close_guide(self) -> None:
        window, self.guide_window = self.guide_window, None
        if window is not None and isValid(window):
            window.close()

    def guide_selector(self, position) -> None:
        self.position = position
        self.free.starter.follow(position)
        if self.guide_window is not None and isValid(self.guide_window):
            self.guide_window.show_selector(position)

    def guide_reading(self, campaign_id: int, reading) -> None:
        window = self.guide_window
        if window is not None and isValid(window) and campaign_id == self.live_id:
            window.show_reading(reading)
