# EasyMeasurement - easymeasurement/ui/instrument_test.py
# Testing an instrument: each check as it finishes, the run kept in its history.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

from ..devices import Capability
from ..devices.instrument_check import FAILED, NOTE, OK, Check, run_checks
from .common import AppContext
from .overlay import Overlay

INTRO = ("Das Messgerät wird kurz verbunden und geprüft. Es wird nichts gestellt und nichts"
         " gemessen. Das Ergebnis kommt ins Geräteprotokoll.")
MARKS = {OK: "✓", NOTE: "!", FAILED: "✗"}


def run_text(checks: list[Check] | tuple, ready: bool) -> str:
    """The run as plain text, to paste somewhere else."""
    lines = [f"{MARKS[c.state]}  {c.title}: {c.detail}" for c in checks]
    return "\n".join(lines + ["", "Bereit für Messungen" if ready else "Nicht bereit"])


class TestWorker(QThread):
    checked = Signal(object)
    finished_with = Signal(object)

    def __init__(self, driver, parent=None):
        super().__init__(parent)
        self.driver = driver

    def run(self) -> None:
        self.finished_with.emit(run_checks(self.driver, date.today(), self.checked.emit))


class InstrumentTestOverlay(Overlay):
    """Starts by itself; closes once the run is in."""

    def __init__(self, app: AppContext, driver_key: str, port: str, label: str, parent=None):
        super().__init__("Messgerät testen", parent)
        self.app, self.driver_key = app, driver_key
        self.connection = "Bluetooth" if port.startswith("bt:") else "USB"
        self.run = None
        intro = QLabel(f"<b>{label}</b><br>{INTRO}")
        intro.setWordWrap(True)
        self.body.addWidget(intro)
        self.lines = QLabel("Verbinde …")
        self.lines.setWordWrap(True)
        self.body.addWidget(self.lines)
        self.copy_button = QPushButton("Als Text kopieren")
        self.copy_button.clicked.connect(self._copy)
        self.copy_button.setEnabled(False)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.copy_button)
        self.body.addLayout(row)
        self.ok_button.setText("Schließen")
        self.ok_button.setEnabled(False)
        self.cancel_button.hide()
        self.checks: list[Check] = []
        driver = app.devices.new_driver(driver_key, port)
        self.capabilities = driver.capabilities
        self.worker = TestWorker(driver, self)
        self.worker.checked.connect(self._checked)
        self.worker.finished_with.connect(self._finished)
        self.worker.start()

    def _checked(self, check: Check) -> None:
        self.checks.append(check)
        self.lines.setText("<br>".join(
            f"{MARKS[c.state]}&nbsp;&nbsp;<b>{c.title}</b>: {c.detail}" for c in self.checks))

    def _finished(self, run) -> None:
        if run.identity is not None and Capability.TEXTS in self.capabilities:
            have = self.app.db.device_text_firmware(self.driver_key) == run.identity.firmware
            check = Check("texts", "Gerätetexte", OK if have else NOTE,
                          "liegen vor" if have else "fehlen: „Einrichten …“ überträgt sie")
            run.checks.append(check)
            self._checked(check)
        self.run = run
        self.app.service.save_instrument_test(self.driver_key, self.connection, run)
        self.hint.setText("Bereit für Messungen." if run.ready else
                          "Nicht bereit für Messungen, siehe ✗.")
        self.ok_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def _copy(self) -> None:
        QGuiApplication.clipboard().setText(run_text(self.run.checks, self.run.ready))

    def reject(self) -> None:
        if not self.worker.isRunning():
            super().reject()

    def _leave(self) -> None:
        self.worker.wait()
        super()._leave()
