# OkeyDocu - okeydocu/ui/repeat_run.py
# The shorter run of a repeat measurement: what stays as it was is passed by.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A repeat runs the same stations as the first measurement, but passes two of them by: the
rotary switch where the instrument already stands right, and the leads where the probes go
where they already are. Where they are is what the run before left: the leads of the last guide
of the run that booked the campaign's latest reading of this kind, and within the run the
leads of the station before. Supply, mode and limits and the measurement itself are always
shown: whether to measure live or dead, and the limits of a new element, are asked every time.
Without an instrument or without an earlier reading at an element nothing is passed by."""

from __future__ import annotations

from ..campaign.last_measured import last_measured_at
from ..campaign.measuring_place import measuring_place
from ..devices.guide import CONNECT, SELECT, Guide
from .station_texts import fits


def terminals(guide: Guide) -> tuple:
    """Where the leads of `guide` go, in order."""
    return tuple((lead.probe, lead.terminal, lead.tool) for lead in guide.leads)


class RepeatRun:
    """Mixed into the measuring window, which holds `app`, `repeat`, `root`, `flow`, `owners`,
    `index`, `position`, `bench` and the guide on it."""

    laid_before: tuple | None = None  # the leads the run before ended with

    def _recall_leads(self, campaign_id: int) -> None:
        if not self.repeat:
            return
        service = self.app.service
        asset_id = last_measured_at(service.db, campaign_id, self.base_guide)
        if asset_id is None:
            return
        place = measuring_place(service, self.base_guide, asset_id, self.root)
        if place.asset_id is not None:
            self.laid_before = terminals(self._chain(place)[-1])

    def _laid_at(self, index: int) -> tuple | None:
        """The leads in place when the run reaches station `index`."""
        earlier = [i for i in range(index) if self.flow[i].kind == CONNECT]
        return terminals(self.owners[earlier[-1]]) if earlier else self.laid_before

    def _passed_by(self, index: int) -> bool:
        if not self.repeat:
            return False
        kind, owner = self.flow[index].kind, self.owners[index]
        if kind == SELECT:
            return owner.selector is not None and fits(owner, self.position)
        if kind == CONNECT:
            return self._laid_at(index) == terminals(owner)
        return False

    def _past_passed(self, index: int, step: int) -> int:
        """`index`, or the next station in the direction of `step` not passed by."""
        step = 1 if step >= 0 else -1
        while 0 < index < len(self.flow) and self._passed_by(index):
            index += step
        return index

    def _leads_passed(self) -> bool:
        """Whether the leads of the guide on the bench were passed by on the way here."""
        first = self.owners.index(self.guide)
        return any(self.flow[i].kind == CONNECT and self._passed_by(i)
                   for i in range(first, self.index))
