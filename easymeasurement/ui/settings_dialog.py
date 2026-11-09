# EasyMeasurement - easymeasurement/ui/settings_dialog.py
# The application's configuration dialog.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QPushButton

from ..devices import find_instruments
from .instrument_setup import InstrumentSetupOverlay
from .overlay import Overlay


class SettingsOverlay(Overlay):
    """The instruments this computer knows, and pairing a new one."""

    def __init__(self, parent=None):
        super().__init__("Messgeräte", parent)
        self.ok_button.setText("Zurück")
        self.cancel_button.hide()
        self.instruments = QListWidget()
        self.instruments.setMinimumHeight(110)
        self.hint = QLabel("Noch kein Messgerät eingerichtet. Per USB angeschlossene Geräte"
                           " erscheinen von selbst.")
        self.hint.setWordWrap(True)
        self.set_up_button = QPushButton("Messgerät über Bluetooth einrichten …")
        self.set_up_button.clicked.connect(self._set_up_instrument)
        row = QHBoxLayout()
        row.addWidget(self.set_up_button)
        row.addStretch()
        self.body.addWidget(self.instruments)
        self.body.addWidget(self.hint)
        self.body.addLayout(row)
        self.refresh()

    def refresh(self) -> None:
        found = find_instruments()
        self.instruments.clear()
        self.instruments.addItems([instrument.label for instrument in found])
        self.hint.setVisible(not found)

    def _set_up_instrument(self) -> None:
        InstrumentSetupOverlay(self).exec()
        self.refresh()
