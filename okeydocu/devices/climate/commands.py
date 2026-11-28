# OkeyDocu - okeydocu/devices/climate/commands.py
# What a climate sensor can be asked over a connection, by the firmware it runs.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Two firmwares are known. The pvvx firmware takes commands on characteristic 0x1F1F and
answers each with a notification that starts with the command byte: 0x22 shows a number and a
face on the display for some seconds and stores nothing, which serves to point a sensor out. The
LYWSD03MMC draws it only with its next reading, some seconds later, and then in turn with its
own readings, while the time shown counts from the command, so it is asked for half a minute.
A whole number from 200 up is drawn without a decimal point; the small number below cannot be
left blank and shows 0;
0x01 gives it a name, which it takes on after the next disconnection. The firmware Xiaomi
ships sends no readings openly; its characteristic EBE0CCC1 holds the latest one."""

from __future__ import annotations

import struct

from .protocols import Reading

COMMANDS = "00001f1f-0000-1000-8000-00805f9b34fb"
XIAOMI_READING = "ebe0ccc1-7a0a-4b0c-8a1a-6ff2997da3a6"
MODEL, FIRMWARE, MAKER = ("00002a24-0000-1000-8000-00805f9b34fb",
                          "00002a26-0000-1000-8000-00805f9b34fb",
                          "00002a29-0000-1000-8000-00805f9b34fb")
SHOW, NAME = 0x22, 0x01
HAPPY = 0x05  # the face that is shown, as the firmware numbers its smileys
MAX_NAME = 20  # characters; Bluetooth names in an advertisement stay short
SHOW_S = 30  # seconds a sensor shows itself
SHOWN = (200, 999)  # whole numbers drawn without a decimal point


def show(number: float, seconds: int) -> bytes:
    """Shows `number` and a face for `seconds` on the display; the firmware takes tenths."""
    return bytes([SHOW]) + struct.pack("<hhHB", round(number * 10), 0, seconds, HAPPY)


def rename(name: str) -> bytes:
    """A new name, or the firmware's own one for an empty name."""
    text = name.encode("ascii", "ignore")[:MAX_NAME]
    return bytes([NAME]) + (text or b"\x00")


def xiaomi_reading(data: bytes) -> Reading | None:
    """Temperature in hundredths of a degree, humidity in percent, battery in millivolts."""
    if len(data) < 5:
        return None
    temperature, humidity, millivolts = struct.unpack("<hBH", data[:5])
    return Reading(temperature / 100, float(humidity), millivolts)


def text(data: bytes) -> str:
    return data.rstrip(b"\x00").decode("utf-8", "replace")
