# OkeyDocu - okeydocu/ui/dial_station.py
# The rotary switch station: the knob turns to the position wanted, the instrument says where.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument is asked for its switch on entering the station and whenever the tester
asks again, never in a steady stream: an answer could otherwise land inside a result being
sent. A moment after the instrument reports a position that serves the measurement, the
guide goes on by itself."""

from __future__ import annotations

from PySide6.QtCore import QTimer

from ..devices.guide import DIAL
from .station_texts import dial_text, fits

AUTO_MS = 900  # a right dial position is shown that long before the guide goes on


class DialStation:
    """Mixed into the measuring window, which holds `guide`, `bench` and `position`."""

    def _enter_dial(self) -> None:
        self.bench.clear_leads()
        self.bench.panel.point_at(f"pos-{self.guide.selector}")
        self._show_dial()
        self.selector_wanted.emit()

    def show_selector(self, position) -> None:
        """A dial position read from the instrument."""
        self.position = position
        if self.station == DIAL:
            self._show_dial()

    def _show_dial(self) -> None:
        right = fits(self.guide, self.position)
        value = self.position.value if self.position is not None else None
        self.bench.panel.show_actual(value, right if self.position is not None else None)
        self.step_text.setText(dial_text(self.guide, self.position))
        self.ask.setVisible(not right)
        if right:
            QTimer.singleShot(AUTO_MS, self._dial_done)

    def _dial_done(self) -> None:
        if self.station == DIAL and fits(self.guide, self.position):
            self.go(DIAL + 1)
