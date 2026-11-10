# EasyMeasurement - easymeasurement/ui/instrument_prepare.py
# Setting an instrument up: what it already has here is checked, what is missing transferred.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QLabel

from ..devices import PREPARING, Capability, DeviceError, driver_info
from ..l10n import N_, tr
from .common import AppContext
from .overlay import Overlay

STEPS = (("identify", N_("Recognise the instrument")), ("texts", N_("Transfer instrument texts")))
MARKS = {"waiting": "○", "running": "…", "done": "✓", "skipped": "–", "failed": "✗"}


def texts_needed(app: AppContext, driver_key: str, firmware: str, capabilities) -> bool:
    """True when this firmware's words for its codes are not here yet."""
    return (Capability.TEXTS in capabilities
            and app.db.device_text_firmware(driver_key) != firmware)


def prepare_if_needed(app: AppContext, driver_key: str, port: str, identity, capabilities,
                      parent) -> None:
    """The first contact after a firmware update, or ever, brings the texts over first."""
    if texts_needed(app, driver_key, identity.firmware, capabilities):
        InstrumentPrepareOverlay(app, driver_key, port, parent).exec()


class PrepareWorker(QThread):
    step = Signal(str, str)  # step, state
    finished_with = Signal(object, object)  # identity, texts or None
    failed = Signal(str)

    def __init__(self, driver, known_firmware: str | None, parent=None):
        super().__init__(parent)
        self.driver, self.known_firmware = driver, known_firmware

    def run(self) -> None:
        try:
            with self.driver:
                self.step.emit("identify", "running")
                identity = self.driver.identify()
                self.step.emit("identify", "done")
                texts = None
                if (Capability.TEXTS in self.driver.capabilities
                        and identity.firmware != self.known_firmware):
                    self.step.emit("texts", "running")
                    texts = self.driver.read_texts()
                self.step.emit("texts", "done" if texts is not None else "skipped")
        except DeviceError as err:
            self.failed.emit(str(err))
        else:
            self.finished_with.emit(identity, texts)


class InstrumentPrepareOverlay(Overlay):
    """Runs by itself on opening. "Later" leaves codes shown as codes until the next try."""

    def __init__(self, app: AppContext, driver_key: str, port: str, parent=None):
        super().__init__(tr("Preparing the instrument"), parent)
        self.app, self.driver_key, self.port = app, driver_key, port
        self.worker: PrepareWorker | None = None
        self.done = False
        info = driver_info(driver_key)
        intro = QLabel(tr(info.preparing if info else PREPARING))
        intro.setWordWrap(True)
        self.body.addWidget(intro)
        self.lines: dict[str, QLabel] = {}
        self.states: dict[str, str] = {}
        for key, text in STEPS:
            self.lines[key] = QLabel()
            self.body.addWidget(self.lines[key])
            self._show_step(key, "waiting", text)
        self.ok_button.setText(tr("Done"))
        self.cancel_button.setText(tr("Later"))
        self.start()

    def _show_step(self, key: str, state: str, text: str | None = None) -> None:
        self.states[key] = state
        label = tr(text or dict(STEPS)[key])
        self.lines[key].setText(f"{MARKS[state]}  {label}")

    def start(self) -> None:
        self.ok_button.setText(tr("Done"))
        self.ok_button.setEnabled(False)
        self.cancel_button.setEnabled(False)  # a transfer is not cut off halfway
        self.hint.clear()
        for key, _ in STEPS:
            self._show_step(key, "waiting")
        driver = self.app.devices.new_driver(self.driver_key, self.port)
        self.worker = PrepareWorker(driver, self.app.db.device_text_firmware(self.driver_key),
                                    self)
        self.worker.step.connect(lambda key, state: self._show_step(key, state))
        self.worker.finished_with.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _finished(self, identity, texts) -> None:
        if texts is not None:
            self.app.db.save_device_texts(self.driver_key, identity.firmware, texts.version,
                                          texts.texts)
        self.done = True
        self.hint.setText(tr("The instrument is ready."))
        self.ok_button.setEnabled(True)
        self.cancel_button.hide()

    def _failed(self, message: str) -> None:
        for key, state in self.states.items():
            if state == "running":
                self._show_step(key, "failed")
        self.hint.setText(message)
        self.ok_button.setText(tr("Try again"))
        self.ok_button.setEnabled(True)
        self.cancel_button.setEnabled(True)

    def accept(self) -> None:
        if self.done:
            super().accept()
        elif self.worker is None or not self.worker.isRunning():
            self.start()

    def _leave(self) -> None:
        if self.worker is not None:
            self.worker.wait()
        super()._leave()
