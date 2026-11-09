# EasyMeasurement - easymeasurement/devices/profitest_prime/discovery.py
# Finds the PROFITEST PRIME by itself: on USB by its IDs, on Bluetooth among paired devices.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import re
import subprocess

from ..base import DeviceError, FoundInstrument
from .channels import Channel, open_channel

log = logging.getLogger(__name__)

DRIVER_KEY = "profitest-prime"
LABEL = "PROFITEST PRIME"
USB_VENDOR, USB_PRODUCT = 0x1CD7, 0x0117
BLUETOOTH_NAME = "PROFITEST"
_PAIRED_RE = re.compile(r"^Device (?P<address>(?:[0-9A-F]{2}:){5}[0-9A-F]{2}) (?P<name>.*)$", re.I)


def usb_ports() -> list[str]:
    from serial.tools import list_ports

    return sorted(
        port.device
        for port in list_ports.comports()
        if (port.vid, port.pid) == (USB_VENDOR, USB_PRODUCT)
    )


def paired_addresses() -> list[str]:
    """Paired devices as BlueZ knows them, whether they are in reach or not."""
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices", "Paired"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as err:
        log.info("Bluetooth nicht abfragbar: %s", err)
        return []
    found = (_PAIRED_RE.match(line.strip()) for line in result.stdout.splitlines())
    return [m["address"] for m in found if m and m["name"].upper().startswith(BLUETOOTH_NAME)]


def find_instruments() -> list[FoundInstrument]:
    """What can be chosen. A paired instrument is listed even while it is switched off."""
    found = [FoundInstrument(DRIVER_KEY, f"{LABEL} (USB)", port) for port in usb_ports()]
    found += [
        FoundInstrument(DRIVER_KEY, f"{LABEL} (Bluetooth)", f"bt:{address}")
        for address in paired_addresses()
    ]
    return found


def open_any() -> Channel:
    """Connect to whichever way works, the cable first."""
    problems = []
    for instrument in find_instruments():
        try:
            return open_channel(instrument.port)
        except DeviceError as err:
            problems.append(str(err))
    if problems:
        raise DeviceError(problems[-1])
    raise DeviceError(
        "Kein Messgerät gefunden. Bitte per USB anschließen oder einmal über Bluetooth einrichten."
    )
