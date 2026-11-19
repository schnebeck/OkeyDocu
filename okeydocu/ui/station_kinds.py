# OkeyDocu - okeydocu/ui/station_kinds.py
# What each kind of station shows and does when the guided measurement enters it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""One method per kind, named after it, so a flow can run its stations in any order. The
words of a station come from the driver; what stays here is how a kind of station is shown."""

from __future__ import annotations

from ..campaign.line_conductors import LINE_CONDUCTORS
from ..devices.guide import MEASURE, PLACE, Station
from ..l10n import tr
from ..vocabulary import setting_name
from .station_texts import actions_text, conductors_text, leads_text, mode_text


def parts_of(actions) -> list[str]:
    return [part for action in actions for part in action.parts]


class StationKinds:
    """Mixed into the measuring window, which holds guide, place, bench and the texts."""

    def _on_display(self) -> None:
        """The instrument's display at this station: dark while the element is chosen, the
        view of the function from then on, with a reading on it while measuring."""
        guide = self.guide
        screen = None if self.kind == PLACE else guide.screen
        if self.kind == MEASURE:
            screen = guide.result_screen or screen
        self.bench.panel.show_screen(screen, self.place.stated)

    def _enter_place(self, station: Station) -> None:
        self.next.setText(tr("Take it ▶") if self.repeat else tr("Prepared – next ▶"))

    def _enter_select(self, station: Station) -> None:
        """A dial is turned where the guide names a position and the panel has one; otherwise
        the station says what to choose. The instrument is asked where it stands either way."""
        if self.has_dial:
            self.next.setText(tr("Turned – next ▶"))
            self._enter_dial()
            return
        self.bench.panel.point_at(*parts_of(station.actions))
        self.step_text.setText(actions_text(station.actions))
        self.selector_wanted.emit()

    def _enter_connect(self, station: Station) -> None:
        self.next.setText(tr("Connected – next ▶"))
        self.step_text.setText(leads_text(self.guide) + actions_text(station.actions))
        self.bench.lay_leads()

    def _enter_prepare(self, station: Station) -> None:
        self.bench.panel.point_at(*parts_of(station.actions))
        self.step_text.setText(actions_text(station.actions))

    def _enter_configure(self, station: Station) -> None:
        parts = parts_of(self.guide.settings) + parts_of(station.actions)
        if station.zoom or parts:
            self.bench.panel.zoom_parts(*station.zoom, *parts)
        self.bench.panel.point_at(*parts)
        self.next.setText(tr("Set – next ▶"))
        advice = conductors_text(self.guide, self.place.stated(LINE_CONDUCTORS),
                                 self.place.has_n)
        self.step_text.setText(mode_text(self.guide, station.actions, self._settings(),
                                         self.place.title, advice))

    def _enter_measure(self, station: Station) -> None:
        self.bench.panel.point_at(*parts_of(self.guide.steps))
        self.step_text.setText(self.measure_text())

    def _settings(self) -> list[tuple[str, str]]:
        """What the element states that is set on the instrument for this measurement."""
        keys = self.guide.element_features if self.guide.owner_feature else ()
        return [(setting_name(key) or key, self.place.stated(key)) for key in keys
                if self.place.stated(key) and setting_name(key)]
