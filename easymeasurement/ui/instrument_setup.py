# EasyMeasurement - easymeasurement/ui/instrument_setup.py
# Sets up an instrument once. Afterwards it only needs to be chosen from the list.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit

from ..devices import DeviceError
from ..devices.profitest_prime import pairing
from ..l10n import N_, tr
from .overlay import Overlay

INSTRUCTIONS = N_(
    "<ol>"
    "<li>Unplug the USB cable.</li>"
    "<li>Turn the rotary switch to <b>Setup</b>.</li>"
    "<li>In the Bluetooth menu, set Bluetooth to <b>on</b> and <b>visible</b>.</li>"
    "<li>Click <b>Set up</b> here and confirm a request on the instrument.</li>"
    "</ol>"
    "This is needed only once. After that the instrument is in the list and only gets chosen."
)


class PairingWorker(QThread):
    progress = Signal(str)
    failed = Signal(str)
    paired = Signal(str)

    def __init__(self, pin: str, parent=None):
        super().__init__(parent)
        self.pin = pin

    def run(self) -> None:
        try:
            address = pairing.pair_instrument(self.pin, self.progress.emit)
        except DeviceError as err:
            self.failed.emit(str(err))
        else:
            self.paired.emit(address)


class InstrumentSetupOverlay(Overlay):
    """The main button pairs; only a paired instrument closes the card by itself."""

    paired = Signal()

    def __init__(self, parent=None):
        super().__init__(tr("Set up instrument"), parent)
        self.worker: PairingWorker | None = None
        self.address = ""  # of the instrument just paired
        self.pin = QLineEdit(pairing.DEFAULT_PIN)
        self.status = QLabel()
        self.status.setWordWrap(True)
        guide = QLabel(tr(INSTRUCTIONS))
        guide.setWordWrap(True)
        self.start_button = self.ok_button
        self.start_button.setText(tr("Set up"))
        self.cancel_button.setText(tr("Back"))
        form = QFormLayout()
        form.addRow(tr("Instrument PIN"), self.pin)
        self.body.addWidget(guide)
        self.body.addLayout(form)
        self.body.addWidget(self.status)

    def first_field(self):
        return self.start_button

    def accept(self) -> None:
        self.start()

    def start(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self.start_button.setEnabled(False)
        self.worker = PairingWorker(self.pin.text().strip(), self)
        self.worker.progress.connect(self.status.setText)
        self.worker.failed.connect(self._failed)
        self.worker.paired.connect(self._paired)
        self.worker.start()

    def _failed(self, text: str) -> None:
        self.status.setText(text)
        self.start_button.setEnabled(True)

    def _paired(self, address: str) -> None:
        self.address = address
        self.status.setText(tr("The instrument is paired."))
        self.paired.emit()
        super().accept()

    def _leave(self) -> None:
        if self.worker is not None:
            self.worker.wait()
        super()._leave()
