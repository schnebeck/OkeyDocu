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
from ..l10n import tr
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
        super().__init__(tr("Instruments"), parent)
        self.app = app
        self.ok_button.setText(tr("Back"))
        self.cancel_button.hide()
        self.instruments = QListWidget()
        self.instruments.setMinimumHeight(110)
        self.hint = QLabel(tr("No instrument set up yet. Instruments connected by USB"
                              " appear by themselves."))
        self.hint.setWordWrap(True)
        self.set_up_button = QPushButton(tr("Set up instrument via Bluetooth …"))
        self.set_up_button.clicked.connect(self._set_up_instrument)
        self.prepare_button = QPushButton(tr("Set up …"))
        self.prepare_button.setToolTip(tr("Checks what the instrument already has here and"
                                          " transfers what is missing. Rotary switch to Setup."))
        self.prepare_button.clicked.connect(self._prepare_chosen)
        self.test_button = QPushButton(tr("Test …"))
        self.test_button.setToolTip(tr("Connects briefly and checks the instrument without setting"
                                       " or measuring anything. The result goes into the"
                                       " instrument log."))
        self.test_button.clicked.connect(self._test_chosen)
        self.log_button = QPushButton(tr("Instrument log …"))
        self.log_button.setToolTip(tr("Tests and campaigns per instrument, without a connection"))
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
            item.setToolTip(tr("Double-click: set up"))
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
