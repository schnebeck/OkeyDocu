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
from ..model import CONDUCTOR, conductor_of
from ..reporting.language import value_text
from ..vocabulary import setting_name
from .limit_text import limit_text
from .station_texts import actions_text, basis_text, conductors_text, fits, leads_text, \
    mode_text, prepared_text, unsuited_text


def parts_of(actions) -> list[str]:
    return [part for action in actions for part in action.parts]


class StationKinds:
    """Mixed into the measuring window, which holds guide, place, bench and the texts."""

    def _view(self, measured: bool = False):
        """The view of the dial position the instrument reported, where that serves the
        measurement, else of the guide's own position."""
        there = self.position.value if fits(self.guide, self.position) else None
        return self.guide.screen_at(there, measured)

    def _on_display(self) -> None:
        """The instrument's display at this station: dark while the element is chosen, the
        view of the function from then on; while measuring with the softkey that shares a
        result, and with the values of the result once it has arrived."""
        screen = None if self.kind == PLACE else self._view(self.kind == MEASURE)
        result = self.reading if self.kind == MEASURE else None
        values = {found.key: value_text(found.quantity.raw)
                  for found in (result.measurement.results if result else ())
                  if found.quantity is not None}
        if result is not None:
            values[CONDUCTOR] = conductor_of(result.measurement.parameters)
        self.bench.panel.show_screen(screen, self.display_stated, values)

    def _to_set(self) -> list[tuple[object, tuple[str, ...]]]:
        """The settings the view on the display has, each with the parts to press. One named
        by its softkey row takes the softkey beside that row and is left out where the view
        does not show the row."""
        view, softkeys = self._view(), self.softkeys
        found = []
        for action in self.guide.settings:
            index = view.softkey(action.key) if view and action.key else None
            if action.key is not None and view is not None and index is None:
                continue
            row = (softkeys[index],) if index is not None and index < len(softkeys) else ()
            found.append((action, action.parts + row))
        return found

    def _enter_place(self, station: Station) -> None:
        self.next.setText(tr("Prepared – next ▶"))

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
        self.step_text.setText(leads_text(self.guide) + prepared_text(self.guide)
                               + actions_text(station.actions))
        self.bench.lay_leads()

    def _enter_prepare(self, station: Station) -> None:
        self.bench.panel.point_at(*parts_of(station.actions))
        self.step_text.setText(actions_text(station.actions))

    def _enter_configure(self, station: Station) -> None:
        parts = [part for _, pressed in self._to_set() for part in pressed]
        parts += parts_of(station.actions)
        if station.zoom:
            self.bench.panel.crop_to(*station.zoom)
        elif parts:
            self.bench.panel.zoom_parts(*parts)
        self.next.setText(tr("Set – next ▶"))
        self._show_configure()

    def _show_configure(self) -> None:
        """What the station says and points at: the settings with the softkeys beside them,
        or the keys of the setting list being looked at."""
        station, to_set = self.flow[self.index], self._to_set()
        if not self._list_on_display():
            self._on_display()
            self.bench.panel.point_at(*[part for _, pressed in to_set for part in pressed],
                                      *parts_of(station.actions))
        advice = self._list_hint()
        advice += conductors_text(self.guide, self.place.stated(LINE_CONDUCTORS),
                                  self.place.has_n)
        advice += unsuited_text(self.guide.function, self.place.stated)
        advice += limit_text(self.guide.function, self.place.stated, self.place.title)
        self.step_text.setText(mode_text([action for action, _ in to_set], station.actions,
                                         self._settings(), self.place.title, advice,
                                         self._list_links())
                               + basis_text(self.guide.function))

    def _enter_measure(self, station: Station) -> None:
        self.bench.panel.point_at(*parts_of(self.guide.steps))
        self.step_text.setText(self.measure_text())

    def _settings(self) -> list[tuple[str, str]]:
        """What the element states that is set on the instrument for this measurement."""
        keys = self.guide.element_features if self.guide.owner_feature else ()
        return [(setting_name(key) or key, self.place.stated(key)) for key in keys
                if self.place.stated(key) and setting_name(key)]
