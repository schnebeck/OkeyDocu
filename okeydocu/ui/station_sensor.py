# OkeyDocu - okeydocu/ui/station_sensor.py
# The stations of a sensor the program takes readings from: point it out, watch it settle.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The window holds the sensor open while it is shown. Once a second it shows the latest
reading and how long it still has to stand; the settle station is left only once it stands,
and the reading is taken by a button at the measure station. Pointing a sensor out takes a
connection of some seconds and runs beside the window."""

from __future__ import annotations

import threading
from datetime import datetime
from html import escape

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QPushButton

from ..devices import DeviceError, LiveReading
from ..devices.guide import IDENTIFY, MEASURE, SETTLE, Station
from ..l10n import decimal, tr
from .station_texts import actions_text

TICK_MS = 1000


class SensorStations:
    """Mixed into the measuring window, which declares the signals `sensor_read` and `pointed`."""

    sensor = None

    def _sensor_setup(self, sensor, advice) -> None:
        """`advice` is the driver's: what the figures of a reading mean for the test."""
        self.sensor = sensor
        self.advice = advice or (lambda values: [])
        self.show_button = QPushButton(tr("Show on the sensor"))
        self.show_button.clicked.connect(self._point_out)
        self.take_button = QPushButton(tr("Take reading"))
        self.take_button.clicked.connect(self._take_reading)
        self.sensor_note = ""  # what the last attempt to reach the sensor said
        self.sensor_timer = QTimer(self, interval=TICK_MS)
        self.sensor_timer.timeout.connect(self._sensor_tick)
        self.pointed.connect(self._pointed)
        for button in (self.show_button, self.take_button):
            button.hide()
        if sensor is not None:
            sensor.open()
            self.sensor_timer.start()

    def _sensor_buttons(self) -> None:
        here = self.sensor is not None
        self.show_button.setVisible(here and self.kind == IDENTIFY)
        self.take_button.setVisible(here and self.kind == MEASURE and self.reading is None)

    def _enter_identify(self, station: Station) -> None:
        self.sensor_note = ""
        self.step_text.setText(actions_text(station.actions))

    def _enter_settle(self, station: Station) -> None:
        self._sensor_tick()

    def _point_out(self) -> None:
        self.show_button.setEnabled(False)
        self.sensor_note = tr("Connecting to the sensor \u2026")
        self._identify_text()

        def work():
            try:
                self.sensor.point_out()
                self.pointed.emit("")
            except DeviceError as error:
                self.pointed.emit(tr(str(error)))
        threading.Thread(target=work, daemon=True, name="point-out").start()

    def _pointed(self, problem: str) -> None:
        self.show_button.setEnabled(True)
        self.sensor_note = problem or tr("The sensor showing a face now is the one chosen.")
        if self.kind == IDENTIFY:
            self._identify_text()

    def _identify_text(self) -> None:
        station = self.flow[self.index]
        self.step_text.setText(actions_text(station.actions)
                               + f"<p><b>{escape(self.sensor_note)}</b></p>")

    def _sensor_tick(self) -> None:
        if self.sensor is None or self.kind not in (SETTLE, MEASURE) or self.reading:
            return
        reading, age, left = self.sensor.latest()
        steady = reading.complete and left <= 0
        if self.kind == SETTLE:
            self.next.setEnabled(steady)
        self.take_button.setEnabled(steady)
        self.step_text.setText(self._live_text(reading, age, left))

    def _live_text(self, reading, age: float, left: float) -> str:
        if not reading.complete:
            return "<p>" + escape(tr("Waiting for the first reading of the sensor \u2026")) + "</p>"
        values = tr("{temperature} \u00b0C, {humidity} % r.H.",
                    temperature=decimal(reading.temperature, 1),
                    humidity=decimal(reading.humidity, 0))
        if left > 0:
            state = tr("Still settling: {seconds} s of steady readings are missing.",
                       seconds=f"{left:.0f}")
        else:
            state = tr("Steady: less than 0.1 \u00b0C of change for a minute.")
        text = f"<p style='font-size:16pt'><b>{escape(values)}</b></p><p>{escape(state)}</p>"
        if age > 30:
            text += "<p>" + escape(tr("Last heard {seconds} s ago.", seconds=f"{age:.0f}")) \
                + "</p>"
        return text + "".join(f"<p>{escape(tr(hint))}</p>"
                              for hint in self.advice({"t_air": reading.temperature}))

    def _take_reading(self) -> None:
        try:
            measurement = self.sensor.take()
        except DeviceError as error:
            self.step_text.setText(f"<p><b>{escape(tr(str(error)))}</b></p>")
            return
        self.sensor_read.emit(LiveReading(measurement, datetime.now()))

    def _sensor_hints(self) -> list[str]:
        """What the temperature taken means for the test."""
        if self.sensor is None or self.reading is None:
            return []
        values = {result.key: result.quantity.base_value
                  for result in self.reading.measurement.results
                  if result.quantity is not None and result.quantity.base_value is not None}
        return [tr(hint) for hint in self.advice(values)]

    def _sensor_close(self) -> None:
        self.sensor_timer.stop()
        if self.sensor is not None:
            self.sensor.close()
