# OkeyDocu - okeydocu/devices/climate/protocols.py
# The ways climate sensors word their readings in a Bluetooth advertisement.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""An advertisement carries service data under a 16-bit UUID. Each protocol knows the UUID
it uses and how its bytes read; one advertisement may hold only part of the readings, so a
sensor's state is built from several (see `merged`). A protocol that is encrypted or does not
send its readings openly decodes to nothing; such a sensor is read over a connection instead.

BTHome v2 (UUID 0xFCD2) is a list of objects, each an id and a value of a size the id fixes;
an object of unknown id ends the decoding, since its size is unknown. The formats of the
custom firmware for Xiaomi thermometers, "pvvx" and "atc1441", both use UUID 0x181A and are
told apart by their length."""

from __future__ import annotations

from dataclasses import dataclass, replace

BTHOME, ENVIRONMENT, XIAOMI = 0xFCD2, 0x181A, 0xFE95


@dataclass(frozen=True)
class Reading:
    """What a sensor reported; None where this advertisement did not say."""

    temperature: float | None = None  # degrees Celsius
    humidity: float | None = None  # percent relative humidity
    battery_mv: int | None = None
    battery_pct: int | None = None
    packet: int | None = None  # counter that changes with every new measurement

    @property
    def complete(self) -> bool:
        return self.temperature is not None and self.humidity is not None


def merged(older: Reading, newer: Reading) -> Reading:
    """The newer reading, its gaps filled from the older one."""
    return replace(older, **{key: value for key, value in vars(newer).items()
                             if value is not None})


def uuid16(uuid: str) -> int | None:
    """The 16-bit part of a Bluetooth base UUID, such as 0000fcd2-0000-1000-8000-00805f9b34fb."""
    text = uuid.lower()
    if len(text) == 36 and text.endswith("-0000-1000-8000-00805f9b34fb") and text[:4] == "0000":
        return int(text[4:8], 16)
    return None


# BTHome object id: size in bytes, signed, factor, field of Reading (or "" to skip).
_BTHOME = {
    0x00: (1, False, 1, "packet"),
    0x01: (1, False, 1, "battery_pct"),
    0x02: (2, True, 0.01, "temperature"),
    0x03: (2, False, 0.01, "humidity"),
    0x04: (3, False, 0.01, ""),  # pressure
    0x05: (3, False, 0.01, ""),  # illuminance
    0x0C: (2, False, 1, "battery_mv"),
    0x0F: (1, False, 1, ""),  # generic boolean
    0x10: (1, False, 1, ""),  # power
    0x11: (1, False, 1, ""),  # opening
    0x2E: (1, False, 1, "humidity"),
    0x2F: (1, False, 1, ""),  # moisture
    0x3A: (1, False, 1, ""),  # button
    0x45: (2, True, 0.1, "temperature"),
}


def bthome(data: bytes) -> Reading | None:
    """BTHome v2; None for another version or encrypted data."""
    if not data or data[0] & 0x01 or data[0] >> 5 != 2:
        return None
    found: dict[str, float | int] = {}
    index = 1
    while index < len(data):
        known = _BTHOME.get(data[index])
        if known is None or index + 1 + known[0] > len(data):
            break
        size, signed, factor, field = known
        raw = int.from_bytes(data[index + 1:index + 1 + size], "little", signed=signed)
        if field:
            found[field] = round(raw * factor, 2) if factor != 1 else raw
        index += 1 + size
    return Reading(**found)


def pvvx(data: bytes) -> Reading | None:
    """Custom format of the pvvx firmware: address, temperature, humidity, battery, counter."""
    if len(data) not in (15, 17):
        return None
    temperature = int.from_bytes(data[6:8], "little", signed=True) / 100
    humidity = int.from_bytes(data[8:10], "little") / 100
    return Reading(temperature, humidity, int.from_bytes(data[10:12], "little"), data[12],
                   data[13])


def atc1441(data: bytes) -> Reading | None:
    """Format of the atc1441 firmware: address, temperature, humidity, battery, counter."""
    if len(data) != 13:
        return None
    temperature = int.from_bytes(data[6:8], "big", signed=True) / 10
    return Reading(temperature, float(data[8]), int.from_bytes(data[10:12], "big"), data[9],
                   data[12])


@dataclass(frozen=True)
class Protocol:
    key: str  # stored with a registered sensor
    label: str
    uuid: int
    decode: object  # bytes -> Reading | None


PROTOCOLS = (
    Protocol("bthome", "BTHome v2", BTHOME, bthome),
    Protocol("pvvx", "pvvx custom", ENVIRONMENT, pvvx),
    Protocol("atc1441", "ATC1441", ENVIRONMENT, atc1441),
)


def decode(service_data: dict[int, bytes]) -> tuple[Protocol, Reading] | None:
    """The first protocol that reads the service data of one advertisement, and its reading."""
    for protocol in PROTOCOLS:
        data = service_data.get(protocol.uuid)
        reading = protocol.decode(data) if data else None
        if reading is not None:
            return protocol, reading
    return None
