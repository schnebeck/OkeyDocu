# OkeyDocu - okeydocu/ui/sensor_enrolment.py
# Making a wireless sensor known to the program: search, identify, name, keep.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Each step talks to the radio for some seconds, so it runs beside the card and the card
says what it is doing. Only one step runs at a time; the card closes once a sensor is kept.
Nothing is chosen for the tester: with several sensors in reach the one to enrol is clicked.
"Back" closes the card at once: a step still running finishes on its own, its result is
dropped, and an enrolment given up keeps nothing. An enrolled sensor carries a green dot in
the list; chosen, it is unenrolled by the same button. Any sensor in reach can be identified.
A sensor can be used as soon as it is listed: identifying or enrolling it ends the search, which
holds the radio, and follows at once."""

from __future__ import annotations

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, \
    QPushButton

from ..devices import DeviceError, Enrolment
from ..l10n import plural, tr
from .button_width import widest
from .overlay import Overlay
from .station_sensor import shown_text

FOUND = Qt.ItemDataRole.UserRole
SCAN_S = 30.0  # a sensor that has just been connected may stay silent for a while
DOT = 12  # pixels of the mark of an enrolled sensor
_RUNNING: set[QThread] = set()  # steps outliving the card they were started from


class Step(QThread):
    failed = Signal(str)
    done = Signal(object)
    news = Signal(object)  # something the work tells on its way

    def __init__(self, work):
        super().__init__()
        self.work = work
        _RUNNING.add(self)
        self.finished.connect(lambda: _RUNNING.discard(self))

    def run(self) -> None:
        try:
            self.done.emit(self.work())
        except DeviceError as error:
            self.failed.emit(tr(str(error)))


def mark(enrolled: bool) -> QIcon:
    """A green dot, or an empty place of its size so that the names stay in line."""
    picture = QPixmap(DOT, DOT)
    picture.fill(Qt.GlobalColor.transparent)
    if enrolled:
        painter = QPainter(picture)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#2e9d4f"))
        painter.drawEllipse(1, 1, DOT - 2, DOT - 2)
        painter.end()
    return QIcon(picture)


class SensorEnrolmentOverlay(Overlay):
    def __init__(self, enrolment: Enrolment, parent=None):
        super().__init__(tr("Enrol sensor"), parent, width=620)
        self.enrolment = enrolment
        self.step: Step | None = None
        self.given_up = False
        self.searching = False
        self.pending = None  # what follows once the search has ended
        self.found = None  # the sensor kept, once it is
        guide = QLabel(tr(enrolment.instructions))
        guide.setWordWrap(True)
        self.sensors = QListWidget()
        self.sensors.setMinimumHeight(120)
        self.sensors.currentRowChanged.connect(lambda _: self._chose())
        self.search_button = QPushButton(tr("Search"))
        self.search_button.clicked.connect(self.search)
        self.show_button = QPushButton(tr("Identify sensor"))
        self.show_button.clicked.connect(self.point_out)
        self.name = QLineEdit()
        self.name.setMaxLength(20)
        self.name.returnPressed.connect(self.accept)
        self.status = QLabel()
        self.status.setWordWrap(True)
        # Name and the three actions are one block below the list; the footer only leaves.
        self.enrol_button = QPushButton()
        self.enrol_button.setFixedWidth(widest(self.enrol_button, (tr("Enrol"), tr("Unenrol"))))
        self.enrol_button.clicked.connect(self.accept)
        self.ok_button.hide()
        self.cancel_button.setText(tr("Back"))
        naming = QHBoxLayout()
        naming.addWidget(QLabel(tr("Name")))
        naming.addWidget(self.name, 1)
        buttons = QHBoxLayout()
        buttons.addWidget(self.search_button)
        buttons.addWidget(self.enrol_button)
        buttons.addWidget(self.show_button)
        buttons.addStretch()
        self.body.addWidget(guide)
        self.body.addWidget(self.sensors)
        self.body.addLayout(naming)
        self.body.addLayout(buttons)
        self.body.addWidget(self.status)
        self._update()

    def first_field(self):
        return self.search_button

    def _chosen(self):
        item = self.sensors.currentItem()
        return item.data(FOUND) if item is not None else None

    def _chose(self) -> None:
        """The sensor's own name stands in the name field, to be kept or changed."""
        found = self._chosen()
        if found is not None:
            self.name.setText(found.name)
        self._update()

    def _busy(self) -> bool:
        return self.step is not None and self.step.isRunning()

    def _enrolled(self) -> bool:
        found = self._chosen()
        return found is not None and self.enrolment.enrolled(found.port)

    def _update(self) -> None:
        free, chosen = not self._busy(), self._chosen() is not None
        usable = chosen and (free or self.searching) and self.pending is None
        self.search_button.setEnabled(free)
        self.show_button.setEnabled(usable)
        self.enrol_button.setEnabled(usable)
        self.enrol_button.setText(tr("Unenrol") if self._enrolled() else tr("Enrol"))
        for row in range(self.sensors.count()):
            item = self.sensors.item(row)
            item.setIcon(mark(self.enrolment.enrolled(item.data(FOUND).port)))

    def _run(self, work, said: str, then, news=None) -> None:
        """`work` takes the step, to tell `news` on its way."""
        if self._busy():
            return
        self.status.setText(said)
        self.step = step = Step(lambda: work(step))
        if news is not None:
            step.news.connect(lambda item: self._heard(news, item))
        self.step.failed.connect(lambda text: self._heard(self.status.setText, text))
        self.step.done.connect(lambda result: self._heard(then, result))
        self.step.finished.connect(lambda: self._heard(self._ended))
        self.step.start()
        self._update()

    def _ended(self) -> None:
        self.searching = False
        then, self.pending = self.pending, None
        self._update()
        if then is not None:
            then()

    def _after_search(self, then) -> bool:
        """While searching, `then` waits for the search to end, which it is asked to."""
        if not self.searching:
            return False
        self.pending = then
        self._update()
        return True

    def _heard(self, then, *result) -> None:
        """What a step reports reaches only a card still open."""
        if not self.given_up:
            then(*result)

    def search(self) -> None:
        """The list fills while the search runs; a sensor chosen meanwhile stays chosen."""
        if self._busy():
            return
        self.sensors.clear()
        self.name.clear()
        self._run(lambda step: self.enrolment.scan(SCAN_S, step.news.emit,
                                                   lambda: self.pending is not None
                                                   or self.given_up),
                  tr("Listening for sensors \u2026"), self._listed, self._add)
        self.searching = True

    def _add(self, sensor) -> None:
        item = QListWidgetItem(sensor.label)
        item.setData(FOUND, sensor)
        self.sensors.addItem(item)
        self._update()

    def _listed(self, found) -> None:
        listed = {self.sensors.item(row).data(FOUND).port for row in range(self.sensors.count())}
        for sensor in found:
            if sensor.port not in listed:
                self._add(sensor)
        self._update()
        self.status.setText(plural(len(found), "{count} sensor in reach.",
                                   "{count} sensors in reach.") if found else
                            tr("No sensor in reach sends a reading in a known protocol."))

    def point_out(self) -> None:
        if self._chosen() is None or self._after_search(self.point_out):
            return
        port = self._chosen().port
        self._run(lambda _: self.enrolment.point_out(port), tr("Connecting to the sensor \u2026"),
                  lambda number: self.status.setText(shown_text(number)))

    def accept(self) -> None:
        """Enrols the sensor chosen, or unenrols it if it is enrolled."""
        if self._chosen() is None or self._after_search(self.accept) or self._busy():
            return
        port, name = self._chosen().port, self.name.text().strip()
        if self._enrolled():
            self.enrolment.forget(port)
            self.status.setText(tr("Unenrolled: {name}", name=name or port))
            self._update()
            return
        self._run(lambda _: self.enrolment.enrol(port, name, lambda: self.given_up),
                  tr("Enrolling the sensor \u2026"), self._kept)

    def _kept(self, found) -> None:
        """The card stays open: the sensor kept is marked, and more can be enrolled."""
        if found is not None:
            self.found = found
            self.status.setText(tr("Enrolled: {name}", name=found.label))
            self._update()

    def reject(self) -> None:
        self.given_up = True
        super().reject()
