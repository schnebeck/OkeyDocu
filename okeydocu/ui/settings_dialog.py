# OkeyDocu - okeydocu/ui/settings_dialog.py
# The application's configuration dialog.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton

from ..devices import DriverInfo, driver_info, find_instruments
from ..l10n import tr
from .instrument_adding import InstrumentAdding
from .instrument_log import InstrumentLogOverlay
from .instrument_prepare import InstrumentPrepareOverlay
from .instrument_setup import InstrumentSetupOverlay
from .instrument_test import InstrumentTestOverlay
from .overlay import Overlay
from .sensor_enrolment import SensorEnrolmentOverlay

FOUND = Qt.ItemDataRole.UserRole


class SettingsOverlay(Overlay):
    """The instruments this computer knows. Setting one up checks what it already has here
    and transfers what is missing; a Bluetooth instrument is paired first. A sensor is enrolled
    instead and listed once it is; it is tested like any instrument, has nothing to set up
    and can be dropped again."""

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
        # One choice for every kind made known once, however many the program supports.
        self.adding = InstrumentAdding()
        self.adding.chosen.connect(self._add)
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
        self.forget_button = QPushButton(tr("Unenrol"))
        self.forget_button.setToolTip(tr("The sensor is no longer offered for campaigns; its"
                                         " readings stay where they are"))
        self.forget_button.clicked.connect(self._forget_chosen)
        self.instruments.currentRowChanged.connect(lambda _: self._update())
        self.instruments.itemDoubleClicked.connect(lambda _: self._prepare_chosen())
        row = QHBoxLayout()  # what is done with the instrument chosen above
        row.addStretch()
        row.addWidget(self.forget_button)
        row.addWidget(self.log_button)
        row.addWidget(self.test_button)
        row.addWidget(self.prepare_button)
        self.body.addWidget(self.instruments)
        self.body.addWidget(self.hint)
        self.body.addLayout(row)
        self.body.addWidget(self.adding)
        self.refresh()

    def refresh(self) -> None:
        found = find_instruments(companions=True)
        self.instruments.clear()
        for instrument in found:
            item = QListWidgetItem(instrument.label)
            item.setData(FOUND, instrument)
            if not self._enrolled(instrument):
                item.setToolTip(tr("Double-click: set up"))
            self.instruments.addItem(item)
        self.hint.setVisible(not found)
        if found:
            self.instruments.setCurrentRow(0)
        self._update()

    @staticmethod
    def _enrolled(found) -> bool:
        return driver_info(found.key).enrolment is not None

    def _chosen(self):
        item = self.instruments.currentItem()
        return item.data(FOUND) if item is not None and self.app is not None else None

    def _update(self) -> None:
        found = self._chosen()
        enrolled = found is not None and self._enrolled(found)
        self.prepare_button.setEnabled(found is not None and not enrolled)
        self.test_button.setEnabled(found is not None)
        self.forget_button.setVisible(enrolled)
        self.log_button.setEnabled(self.app is not None)

    def _add(self, info: DriverInfo) -> None:
        if info.pairing is not None:
            self._pair(info)
        else:
            self._enrol(info)

    def _enrol(self, info: DriverInfo) -> None:
        SensorEnrolmentOverlay(info.enrolment, self).exec()
        self.refresh()

    def _forget_chosen(self) -> None:
        found = self._chosen()
        if found is not None and self._enrolled(found):
            driver_info(found.key).enrolment.forget(found.port)
            self.refresh()

    def _pair(self, info: DriverInfo) -> None:
        pairing = InstrumentSetupOverlay(info.pairing, self)
        if pairing.exec() and pairing.port and self.app is not None:
            self.prepare(info.key, pairing.port)
        self.refresh()

    def _test_chosen(self) -> None:
        found = self._chosen()
        if found is not None:
            InstrumentTestOverlay(self.app, found.key, found.port, found.label, self).exec()

    def _prepare_chosen(self) -> None:
        found = self._chosen()
        if found is not None and not self._enrolled(found):
            self.prepare(found.key, found.port)

    def prepare(self, driver_key: str, port: str) -> None:
        InstrumentPrepareOverlay(self.app, driver_key, port, self).exec()
