# OkeyDocu - okeydocu/ui/dial_station.py
# The rotary switch station: the knob turns to the position wanted, the instrument says where.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument is asked for its switch every half second while the window is open, except
at the measure station: the instrument writes a result in pieces, and an answer could land
inside one being sent. Each report turns the drawn knob. A moment after the instrument
reports a position that serves the measurement, the dial station goes on by itself, with or
without a dial drawn."""

from __future__ import annotations

from PySide6.QtCore import QTimer

from ..devices.guide import MEASURE, SELECT
from .station_texts import dial_text, fits

AUTO_MS = 900  # a right dial position is shown that long before the guide goes on
POLL_MS = 500


class DialStation:
    """Mixed into the measuring window, which holds `guide`, `bench`, `position` and the
    timer `poll`."""

    def _poll_selector(self) -> None:
        if self.kind != MEASURE and self.guide.selector is not None:
            self.selector_wanted.emit()

    def _enter_dial(self) -> None:
        self.bench.clear_leads()
        self.bench.panel.point_at()
        self._show_dial()
        self.selector_wanted.emit()

    def show_selector(self, position) -> None:
        """A dial position read from the instrument."""
        known = self.position is not None and position is not None
        unchanged = known and position.value == self.position.value
        self.position = position
        self._show_actual()
        if self.kind != SELECT or unchanged:
            return
        if self.has_dial:
            self._show_dial()
        elif fits(self.guide, position):
            QTimer.singleShot(AUTO_MS, self._dial_done)

    def _show_actual(self) -> None:
        value = self.position.value if self.position is not None else None
        right = fits(self.guide, self.position) if self.position is not None else None
        self.bench.panel.show_actual(value, right)

    def _show_dial(self) -> None:
        self._show_actual()
        self.step_text.setText(dial_text(self.guide, self.position))
        if fits(self.guide, self.position):
            QTimer.singleShot(AUTO_MS, self._dial_done)

    def _dial_done(self) -> None:
        if self.kind == SELECT and fits(self.guide, self.position):
            self.go(self.index + 1)
