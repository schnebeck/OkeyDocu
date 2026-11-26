# OkeyDocu - okeydocu/ui/guide_run.py
# The run of a guided measurement: the stations of the guide suited to the element and of
# those that follow it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The driver's guide may name another one for what the element states, and guides that follow
in the same run. Their flows stand one behind the other in the station bar; each station knows
the guide it belongs to, whose leads, settings, steps and result it shows. A reading is kept
for the guide it ends, so it is there when the run reaches that guide's measure station."""

from __future__ import annotations

from dataclasses import replace

from ..campaign.expected_voltage import between_lines, misfits, nominal_frequency, \
    off_frequency
from ..campaign.line_conductors import LINE_CONDUCTORS
from ..devices.guide import CONNECT, MEASURE, Guide
from ..l10n import tr
from .station_texts import measure_text

NOMINAL, FREQUENCY = "nominal_voltage", "supply_frequency"


def _without_n(guide: Guide, has_n: bool | None) -> Guide:
    """Without N at the test point the lead to it stays where it is."""
    if has_n is not False:
        return guide
    return replace(guide, leads=tuple(lead for lead in guide.leads
                                      if not lead.terminal.endswith("_n")))


class GuideRun:
    """Mixed into the measuring window, which holds `base_guide`, `bar`, `bench`, `index` and
    the place as entered in `shown`."""

    def _chain(self, place) -> list[Guide]:
        """The guides of a run at `place`, each with the leads its test point has."""
        return [_without_n(guide, place.has_n)
                for guide in self.base_guide.suited(place.stated).chain()]

    def _plan(self) -> None:
        """Lays the run out anew for the element as entered so far."""
        chain = self._chain(self.shown)
        self.owners = tuple(guide for guide in chain for _ in guide.flow)
        self.flow = tuple(station for guide in chain for station in guide.flow)
        self.bar.set_names(tuple(station.heading() for station in self.flow))
        self.guide = self.owners[min(self.index, len(self.owners) - 1)]
        self._on_bench()

    def _on_bench(self) -> None:
        self.bench.show_guide(self.guide, self.shown.lines(self.guide.drawing_features),
                              self.shown.poles, self.shown.n_left)

    def _take_guide(self) -> None:
        """Entering a station of another guide puts that guide on the bench, its leads laid
        where the run is past its leads station."""
        guide = self.owners[self.index]
        if guide is self.guide:
            return
        self.guide = guide
        self._on_bench()
        first = self.owners.index(guide)
        kinds = [station.kind for station in self.flow[first:self.index]]
        if CONNECT in kinds:
            self.bench.finish()

    @property
    def reading(self):
        """The result the guide of the station on screen waits for, once it is there."""
        return self.readings.get(self.guide.function)

    def show_reading(self, reading) -> None:
        """A result from the instrument, kept for each guide of the run it ends."""
        function = reading.measurement.function
        for guide in set(self.owners):
            if guide.ended_by(function):
                self.readings[guide.function] = reading
        if self.kind == MEASURE and self.guide.ended_by(function):
            self.bench.panel.point_at()
            self.step_text.setText(self.measure_text())
            self._on_display()

    def measure_text(self) -> str:
        return measure_text(self.guide, self.reading, self._voltage_warnings())

    def _voltage_warnings(self) -> list[str]:
        """Voltages of the result that do not fit what the element lets expect."""
        if self.reading is None:
            return []
        system = between_lines(self.place.stated(LINE_CONDUCTORS), self.place.stated(NOMINAL))
        mains = nominal_frequency(self.place.stated(FREQUENCY))
        off = [tr("{label} {value}: within 1 % of {expected} Hz is what a machine is built"
                  " for (EN 60204-1, 4.3.2).",
                  label=label, value=value, expected=f"{expected:.0f}")
               for label, value, expected in off_frequency(self.reading.measurement, mains)]
        return [tr("{label} {value}: about {expected} V are expected here. Check the"
                   " connection and what the element states.",
                   label=label, value=value, expected=f"{expected:.0f}")
                for label, value, expected in misfits(self.reading.measurement, system)] + off
