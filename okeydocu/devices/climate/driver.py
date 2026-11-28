# OkeyDocu - okeydocu/devices/climate/driver.py
# A climate sensor as an instrument: it listens all along and measures when asked.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""While open, a thread listens to the sensor in short turns and keeps its latest reading and
how steady it is. A sensor that sends nothing openly is read over a connection now and then.
A command needs the radio to itself: it waits for the end of a turn, connects, and the next
turn begins after it. A measurement is taken when the program asks, from the latest reading;
the sensor has no clock and no memory, so its time is the laptop's."""

from __future__ import annotations

import random
import threading
import time
import uuid
from datetime import datetime

from ...l10n import tr
from ...model import DeviceIdentity, MeterMeasurement, Quantity, ResultValue, Verdict
from ..base import Capability, DeviceError, LiveReading, MeterDriver
from . import commands
from .bluez import Bluez
from .protocols import Reading, decode, merged
from .settling import Settling

TURN_S, POLL_S, STALE_S = 8.0, 10.0, 120.0
FUNCTION = "ambient"


def measurement(reading: Reading, moment: datetime) -> MeterMeasurement:
    """The figures of one reading, without a verdict: no standard sets a limit for them."""
    def value(key, label, text):
        return ResultValue(key, label, Quantity.parse(text), Verdict.NOT_EVALUATED, "", "")
    results = [value("t_air", "T", f"{reading.temperature:.2f}\u00b0C"),
               value("rh", "r.H.", f"{reading.humidity:.1f}%")]
    if reading.battery_mv:
        results.append(value("u_battery", "U_batt", f"{reading.battery_mv / 1000:.3f}V"))
    return MeterMeasurement(str(uuid.uuid4()), FUNCTION, moment.replace(microsecond=0),
                            Verdict.NOT_EVALUATED, results=tuple(results))


class ClimateSensor(MeterDriver):
    capabilities = Capability.TAKE

    def __init__(self, port: str = "", **_):
        if not port:
            raise DeviceError(tr("No sensor is chosen."))
        self.address = port
        self.reading = Reading()
        self.heard_at = 0.0
        self.settling = Settling()
        self.protocol = ""
        self._radio = threading.Lock()
        self._waiting = threading.Event()  # a command waits for the radio
        self._stop = threading.Event()
        self.aborted = threading.Event()  # a test waiting for a reading gives up
        self._thread: threading.Thread | None = None
        self._on_reading = None

    def open(self) -> None:
        if self._thread is None:
            self._stop.clear()
            self._thread = threading.Thread(target=self._listen, daemon=True,
                                            name="climate-sensor")
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=TURN_S + 5)
            self._thread = None
        self._on_reading = None

    def _listen(self) -> None:
        polled = 0.0
        while not self._stop.is_set():
            with self._radio:
                try:
                    bus = Bluez()
                except DeviceError:
                    self._stop.wait(POLL_S)
                    continue
                try:
                    for advert in bus.listen(TURN_S):
                        if advert.address == self.address:
                            self._heard(decode(advert.service_data))
                finally:
                    bus.close()
            if self._waiting.is_set():  # a lock is not fair: give the command its turn
                self._stop.wait(0.5)
                continue
            if self.protocol in ("", "xiaomi") and time.monotonic() - polled > POLL_S:
                polled = time.monotonic()
                try:
                    self._heard(self._read_xiaomi())
                except DeviceError:
                    pass

    def _heard(self, found) -> None:
        if found is None:
            return
        protocol, reading = found if isinstance(found, tuple) else ("xiaomi", found)
        self.protocol = getattr(protocol, "key", protocol)
        self.reading = merged(self.reading, reading)
        self.heard_at = time.monotonic()
        if reading.temperature is not None:
            self.settling.add(self.heard_at, reading.temperature)

    def latest(self) -> tuple[Reading, float, float]:
        """The latest reading, its age and the seconds of steady readings still missing, all
        in seconds; 0 missing: the sensor has settled."""
        now = time.monotonic()
        age = now - self.heard_at if self.heard_at else float("inf")
        return self.reading, age, self.settling.left_s(now)

    def _connected(self, work):
        """Runs `work(bus)` on a connection to the sensor, with the radio to itself."""
        self._waiting.set()
        with self._radio:
            self._waiting.clear()
            bus = Bluez()
            try:
                if bus.find(15, lambda advert: advert.address == self.address) is None:
                    raise DeviceError(tr("The sensor is not in reach."))
                bus.connect(self.address)
                try:
                    return work(bus)
                finally:
                    bus.disconnect(self.address)
            finally:
                bus.close()

    def _read_xiaomi(self) -> Reading | None:
        def work(bus):
            return commands.xiaomi_reading(bus.read(bus.characteristic(
                self.address, commands.XIAOMI_READING)))
        return self._connected(work)

    def identify(self) -> DeviceIdentity:
        def work(bus):
            found = {}
            for key, uuid_ in (("model", commands.MODEL), ("firmware", commands.FIRMWARE),
                               ("manufacturer", commands.MAKER)):
                try:
                    found[key] = commands.text(bus.read(bus.characteristic(self.address, uuid_)))
                except DeviceError:
                    found[key] = ""
            return DeviceIdentity(serial_no=self.address, name=bus.name(self.address), **found)
        return self._connected(work)

    def point_out(self, seconds: int = commands.SHOW_S) -> int:
        """Shows a number of its own and a face on the display of this very sensor; the number,
        for the tester to look for among several sensors."""
        number = random.randint(*commands.SHOWN)
        # The display shows what was written; its echo is not waited for.
        self._connected(lambda bus: bus.ask(bus.characteristic(self.address, commands.COMMANDS),
                                            commands.show(number, seconds), needed=False))
        return number

    def rename(self, name: str) -> None:
        self._connected(lambda bus: bus.ask(bus.characteristic(self.address, commands.COMMANDS),
                                            commands.rename(name)))

    def abort(self) -> None:
        self.aborted.set()

    def read_clock(self) -> datetime:
        return datetime.now()  # no clock of its own: the laptop's time stands for it

    def read_measurements(self) -> list[MeterMeasurement]:
        return []

    def subscribe_live(self, on_reading, on_state=None) -> None:
        self._on_reading = on_reading
        self.open()

    def unsubscribe_live(self) -> None:
        self._on_reading = None

    def take(self) -> MeterMeasurement:
        """A measurement from the latest reading, sent like a pushed one."""
        reading, age, _ = self.latest()
        if not reading.complete or age > STALE_S:
            raise DeviceError(tr("The sensor has not sent a reading yet."))
        taken = measurement(reading, datetime.now())
        if self._on_reading is not None:
            self._on_reading(LiveReading(taken, datetime.now()))
        return taken
