# OkeyDocu - okeydocu/devices/climate/info.py
# What the program knows of climate sensors: how they are found, enrolled and guided.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Only enrolled sensors are offered, so a stranger's sensor in reach never shows up in a
campaign. Enrolling lists what sends a reading in one of the known protocols, lets the chosen
one show itself, gives it the name chosen and keeps what it tells of itself."""

from __future__ import annotations

from ...l10n import N_, tr
from ...model import DeviceIdentity
from ..base import DeviceError, FoundInstrument
from ..driver_info import DriverInfo, Enrolment
from . import guides
from .bluez import Bluez
from .driver import ClimateSensor
from .known import KnownSensor, forget, known_sensors, remember
from .protocols import decode

KEY = "climate"
INSTRUCTIONS = N_("<p>Supported are sensors such as the Xiaomi LYWSD03MMC running the pvvx"
                  " firmware (ATC_MiThermometer), which sends its readings as BTHome v2, in"
                  " the pvvx or in the ATC1441 format. Readings of the ATC1441 firmware are"
                  " read as well; such a sensor can be neither identified nor named. With the"
                  " firmware it is sold with a sensor sends no readings and is not listed.</p>"
                  "<p>Search, choose a sensor and identify it: its display shows the number"
                  " named below. Enter a name and enrol it.</p>")


def find() -> list[FoundInstrument]:
    return [FoundInstrument(KEY, tr("Climate sensor {name}", name=sensor.name), sensor.address)
            for sensor in known_sensors()]


def scan(seconds: float, heard=lambda found: None, stopped=lambda: False) -> list[FoundInstrument]:
    """Every sensor heard within `seconds`, each told to `heard` the moment it is; `stopped`
    ends the search early."""
    found: dict[str, FoundInstrument] = {}
    bus = Bluez()
    try:
        for advert in bus.listen(seconds, stopped):
            decoded = decode(advert.service_data)
            if decoded is not None and advert.address not in found:
                protocol, reading = decoded
                label = f"{advert.name or advert.address}  {tr(protocol.label)}"
                if reading.temperature is not None:
                    label += f"  {reading.temperature:.1f} \u00b0C"
                found[advert.address] = FoundInstrument(KEY, label, advert.address,
                                                        advert.name or "")
                heard(found[advert.address])
    finally:
        bus.close()
    return list(found.values())


def point_out(port: str) -> int:
    return ClimateSensor(port).point_out()


def enrol(port: str, name: str, given_up=lambda: False) -> FoundInstrument | None:
    """Nothing is kept once the tester has given up, however far it got. Without a name
    given the sensor keeps the one it calls itself."""
    sensor = ClimateSensor(port)
    identity = sensor.identify()
    if given_up():
        return None
    if name and name != identity.name:
        try:
            sensor.rename(name)
        except DeviceError:
            pass  # kept under the name chosen; the sensor keeps calling itself what it did
    if given_up():
        return None
    name = name or identity.name
    remember(KnownSensor(port, name or identity.model, "", identity.manufacturer,
                         identity.model, identity.firmware))
    return FoundInstrument(KEY, tr("Climate sensor {name}", name=name or identity.model), port)


def identity_of(port: str) -> DeviceIdentity:
    """What the sensor told of itself when it was enrolled; its address stands for a serial
    number, which it has none of."""
    sensor = next((sensor for sensor in known_sensors() if sensor.address == port), None)
    if sensor is None:
        raise DeviceError(tr("The sensor is not enrolled."))
    return DeviceIdentity(sensor.manufacturer, sensor.model, port, sensor.firmware,
                          name=sensor.name)


DRIVER = DriverInfo(
    key=KEY,
    label=N_("Climate sensor"),
    factory=ClimateSensor,
    find=find,
    guide=guides.guide_for,
    guided=tuple(guides.GUIDES),
    enrolment=Enrolment(INSTRUCTIONS, scan, point_out, enrol,
                        forget, lambda port: any(sensor.address == port
                                                 for sensor in known_sensors())),
    companion=True,
    calibrated=False,
    advice=guides.hints,
    identity_of=identity_of,
)
