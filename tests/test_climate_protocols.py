# OkeyDocu - tests/test_climate_protocols.py
# Decoding the advertisements of climate sensors.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.devices.climate.protocols import (BTHOME, ENVIRONMENT, Reading, atc1441, bthome,
                                                decode, merged, pvvx, uuid16)

ADDRESS = bytes.fromhex("554433221100")  # invented


def test_bthome_reads_temperature_humidity_and_battery_from_its_two_kinds_of_packet():
    climate = bthome(bytes.fromhex("4000b2016402530803 9b0e".replace(" ", "")))
    assert climate == Reading(21.31, 37.39, None, 100, 0xB2)
    power = bthome(bytes.fromhex("4000b20cce0b10001101"))
    assert power.battery_mv == 3022 and power.temperature is None
    assert merged(climate, power) == Reading(21.31, 37.39, 3022, 100, 0xB2)
    assert merged(climate, power).complete and not power.complete


def test_bthome_refuses_encryption_and_other_versions_and_stops_at_an_unknown_object():
    assert bthome(bytes.fromhex("41000102")) is None  # encrypted
    assert bthome(bytes.fromhex("2000016402")) is None  # version 1
    partial = bthome(bytes.fromhex("4000010164 99aaaa".replace(" ", "")))
    assert partial == Reading(battery_pct=100, packet=1)
    assert bthome(bytes.fromhex("4002")) == Reading()  # a cut object is left out


def test_bthome_takes_negative_temperatures_and_the_coarse_objects():
    assert bthome(bytes.fromhex("4045ceff2e3c")) == Reading(temperature=-5.0, humidity=60)


def test_the_custom_formats_of_the_xiaomi_firmware():
    custom = ADDRESS + (-123).to_bytes(2, "little", signed=True) + (5555).to_bytes(2, "little") \
        + (2950).to_bytes(2, "little") + bytes([77, 9, 0])
    assert pvvx(custom) == Reading(-1.23, 55.55, 2950, 77, 9)
    old = ADDRESS[::-1] + (215).to_bytes(2, "big") + bytes([41, 88]) \
        + (3010).to_bytes(2, "big") + bytes([5])
    assert atc1441(old) == Reading(21.5, 41.0, 3010, 88, 5)
    assert pvvx(old) is None and atc1441(custom) is None


def test_the_protocol_is_found_by_uuid_and_length():
    old = ADDRESS[::-1] + (215).to_bytes(2, "big") + bytes([41, 88]) \
        + (3010).to_bytes(2, "big") + bytes([5])
    protocol, reading = decode({ENVIRONMENT: old})
    assert protocol.key == "atc1441" and reading.humidity == 41.0
    assert decode({BTHOME: bytes.fromhex("4045ceff")})[0].key == "bthome"
    assert decode({0xFE95: bytes(20)}) is None and decode({}) is None


@pytest.mark.parametrize("uuid, short", [
    ("0000fcd2-0000-1000-8000-00805f9b34fb", 0xFCD2),
    ("0000181A-0000-1000-8000-00805F9B34FB", 0x181A),
    ("ebe0ccb0-7a0a-4b0c-8a1a-6ff2997da3a6", None),
])
def test_a_base_uuid_has_a_short_form(uuid, short):
    assert uuid16(uuid) == short
