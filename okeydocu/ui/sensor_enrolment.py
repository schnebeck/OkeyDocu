# OkeyDocu - okeydocu/ui/sensor_enrolment.py
# Making a wireless sensor known to the program: search, point out, name, keep.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Each step talks to the radio for some seconds, so it runs beside the card and the card
says what it is doing. Only one step runs at a time; the card closes once a sensor is kept."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget, \
    QListWidgetItem, QPushButton

from ..devices import DeviceError, Enrolment
from ..l10n import tr
from .overlay import Overlay

FOUND = Qt.ItemDataRole.UserRole
SCAN_S = 10.0


class Step(QThread):
    failed = Signal(str)
    done = Signal(object)

    def __init__(self, work, parent=None):
        super().__init__(parent)
        self.work = work

    def run(self) -> None:
        try:
            self.done.emit(self.work())
        except DeviceError as error:
            self.failed.emit(tr(str(error)))


class SensorEnrolmentOverlay(Overlay):
    def __init__(self, enrolment: Enrolment, parent=None):
        super().__init__(tr("Enrol sensor"), parent, width=620)
        self.enrolment = enrolment
        self.step: Step | None = None
        self.found = None  # the sensor kept, once it is
        guide = QLabel(tr(enrolment.instructions))
        guide.setWordWrap(True)
        self.sensors = QListWidget()
        self.sensors.setMinimumHeight(120)
        self.sensors.currentRowChanged.connect(lambda _: self._update())
        self.search_button = QPushButton(tr("Search"))
        self.search_button.clicked.connect(self.search)
        self.show_button = QPushButton(tr("Show on the sensor"))
        self.show_button.clicked.connect(self.point_out)
        self.name = QLineEdit()
        self.name.setMaxLength(20)
        self.name.setPlaceholderText(tr("as it is to be called, e.g. a number on its back"))
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.ok_button.setText(tr("Enrol"))
        self.cancel_button.setText(tr("Back"))
        buttons = QHBoxLayout()
        buttons.addWidget(self.search_button)
        buttons.addWidget(self.show_button)
        buttons.addStretch()
        form = QFormLayout()
        form.addRow(tr("Name"), self.name)
        self.body.addWidget(guide)
        self.body.addWidget(self.sensors)
        self.body.addLayout(buttons)
        self.body.addLayout(form)
        self.body.addWidget(self.status)
        self._update()

    def first_field(self):
        return self.search_button

    def _chosen(self):
        item = self.sensors.currentItem()
        return item.data(FOUND) if item is not None else None

    def _busy(self) -> bool:
        return self.step is not None and self.step.isRunning()

    def _update(self) -> None:
        free, chosen = not self._busy(), self._chosen() is not None
        self.search_button.setEnabled(free)
        self.show_button.setEnabled(free and chosen)
        self.ok_button.setEnabled(free and chosen)

    def _run(self, work, said: str, then) -> None:
        if self._busy():
            return
        self.status.setText(said)
        self.step = Step(work, self)
        self.step.failed.connect(self._failed)
        self.step.done.connect(then)
        self.step.finished.connect(self._update)
        self.step.start()
        self._update()

    def _failed(self, text: str) -> None:
        self.status.setText(text)

    def search(self) -> None:
        self._run(lambda: self.enrolment.scan(SCAN_S), tr("Listening for sensors \u2026"),
                  self._listed)

    def _listed(self, found) -> None:
        self.sensors.clear()
        for sensor in found:
            item = QListWidgetItem(sensor.label)
            item.setData(FOUND, sensor)
            self.sensors.addItem(item)
        if found:
            self.sensors.setCurrentRow(0)
        self.status.setText(tr("{count} sensors in reach.", count=len(found)) if found else
                            tr("No sensor in reach sends a reading in a known protocol."))

    def point_out(self) -> None:
        port = self._chosen().port
        self._run(lambda: self.enrolment.point_out(port), tr("Connecting to the sensor \u2026"),
                  lambda _: self.status.setText(
                      tr("The sensor showing a face now is the one chosen.")))

    def accept(self) -> None:
        if self._chosen() is None:
            return
        port, name = self._chosen().port, self.name.text().strip()
        self._run(lambda: self.enrolment.enrol(port, name), tr("Enrolling the sensor \u2026"),
                  self._kept)

    def _kept(self, found) -> None:
        self.found = found
        super().accept()

    def _leave(self) -> None:
        if self.step is not None:
            self.step.wait()
        super()._leave()
