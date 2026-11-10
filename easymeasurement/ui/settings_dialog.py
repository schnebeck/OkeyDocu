# EasyMeasurement - easymeasurement/ui/settings_dialog.py
# The application's configuration dialog.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton

from ..devices import find_instruments
from ..devices.profitest_prime.discovery import DRIVER_KEY
from .instrument_log import InstrumentLogOverlay
from .instrument_prepare import InstrumentPrepareOverlay
from .instrument_setup import InstrumentSetupOverlay
from .instrument_test import InstrumentTestOverlay
from .overlay import Overlay

FOUND = Qt.ItemDataRole.UserRole


class SettingsOverlay(Overlay):
    """The instruments this computer knows. Setting one up checks what it already has here
    and transfers what is missing; a Bluetooth instrument is paired first."""

    def __init__(self, parent=None, app=None):
        super().__init__("Messgeräte", parent)
        self.app = app
        self.ok_button.setText("Zurück")
        self.cancel_button.hide()
        self.instruments = QListWidget()
        self.instruments.setMinimumHeight(110)
        self.hint = QLabel("Noch kein Messgerät eingerichtet. Per USB angeschlossene Geräte"
                           " erscheinen von selbst.")
        self.hint.setWordWrap(True)
        self.set_up_button = QPushButton("Messgerät über Bluetooth einrichten …")
        self.set_up_button.clicked.connect(self._set_up_instrument)
        self.prepare_button = QPushButton("Einrichten …")
        self.prepare_button.setToolTip("Prüft, was das Messgerät hier schon hat, und überträgt,"
                                       " was fehlt. Drehrad dafür auf Setup.")
        self.prepare_button.clicked.connect(self._prepare_chosen)
        self.test_button = QPushButton("Testen …")
        self.test_button.setToolTip("Verbindet kurz und prüft das Messgerät, ohne etwas zu stellen"
                                    " oder zu messen. Das Ergebnis kommt ins Geräteprotokoll.")
        self.test_button.clicked.connect(self._test_chosen)
        self.log_button = QPushButton("Geräteprotokoll …")
        self.log_button.setToolTip("Tests und Kampagnen je Messgerät, ohne Verbindung")
        self.log_button.clicked.connect(
            lambda: InstrumentLogOverlay(self.app, self).exec() if self.app else None)
        self.instruments.currentRowChanged.connect(lambda _: self._update())
        self.instruments.itemDoubleClicked.connect(lambda _: self._prepare_chosen())
        row = QHBoxLayout()  # what is done with the instrument chosen above
        row.addStretch()
        row.addWidget(self.log_button)
        row.addWidget(self.test_button)
        row.addWidget(self.prepare_button)
        pair_row = QHBoxLayout()
        pair_row.addWidget(self.set_up_button)
        pair_row.addStretch()
        self.body.addWidget(self.instruments)
        self.body.addWidget(self.hint)
        self.body.addLayout(row)
        self.body.addLayout(pair_row)
        self.refresh()

    def refresh(self) -> None:
        found = find_instruments()
        self.instruments.clear()
        for instrument in found:
            item = QListWidgetItem(instrument.label)
            item.setData(FOUND, instrument)
            item.setToolTip("Doppelklick: einrichten")
            self.instruments.addItem(item)
        self.hint.setVisible(not found)
        if found:
            self.instruments.setCurrentRow(0)
        self._update()

    def _update(self) -> None:
        chosen = self.app is not None and self.instruments.currentRow() >= 0
        self.prepare_button.setEnabled(chosen)
        self.test_button.setEnabled(chosen)
        self.log_button.setEnabled(self.app is not None)

    def _set_up_instrument(self) -> None:
        pairing = InstrumentSetupOverlay(self)
        if pairing.exec() and pairing.address and self.app is not None:
            self.prepare(DRIVER_KEY, f"bt:{pairing.address}")
        self.refresh()

    def _test_chosen(self) -> None:
        item = self.instruments.currentItem()
        if item is not None and self.app is not None:
            found = item.data(FOUND)
            InstrumentTestOverlay(self.app, found.key, found.port, found.label, self).exec()

    def _prepare_chosen(self) -> None:
        item = self.instruments.currentItem()
        if item is not None and self.app is not None:
            found = item.data(FOUND)
            self.prepare(found.key, found.port)

    def prepare(self, driver_key: str, port: str) -> None:
        InstrumentPrepareOverlay(self.app, driver_key, port, self).exec()
