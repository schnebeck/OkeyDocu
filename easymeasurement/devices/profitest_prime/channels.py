# EasyMeasurement - easymeasurement/devices/profitest_prime/channels.py
# Byte channels to the PROFITEST PRIME: USB serial port and Bluetooth RFCOMM.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import re
import socket
from typing import Protocol

from ..base import DeviceError

log = logging.getLogger(__name__)

BLUETOOTH_CHANNEL = 1
_BLUETOOTH_RE = re.compile(r"^bt:(?P<address>(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})(?:/(?P<channel>\d+))?$")


class SerialPort(Protocol):
    in_waiting: int

    def read(self, size: int) -> bytes: ...
    def write(self, data: bytes) -> int: ...
    def flush(self) -> None: ...
    def close(self) -> None: ...


class Channel(Protocol):
    def read(self) -> bytes:
        """Return what has arrived, b"" if nothing did. Raises OSError when lost."""

    def write(self, data: bytes) -> None: ...
    def close(self) -> None: ...


class SerialChannel:
    def __init__(self, port: SerialPort):
        self._port = port

    def read(self) -> bytes:
        return self._port.read(self._port.in_waiting or 1)

    def write(self, data: bytes) -> None:
        self._port.write(data)
        self._port.flush()

    def close(self) -> None:
        self._port.close()


class RfcommChannel:
    """Bluetooth serial port as a plain socket: no rfcomm tool and no root needed."""

    def __init__(self, address: str, channel: int = BLUETOOTH_CHANNEL, timeout_s: float = 20.0):
        self._socket = socket.socket(
            socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
        )
        self._socket.settimeout(timeout_s)
        try:
            self._socket.connect((address, channel))
        except OSError as err:
            self._socket.close()
            log.info("Bluetooth-Verbindung zu %s fehlgeschlagen: %s", address, err)
            raise DeviceError(
                "Das Messgerät antwortet nicht. Bitte einschalten und Bluetooth aktivieren."
            ) from err
        self._socket.settimeout(0.05)

    def read(self) -> bytes:
        try:
            data = self._socket.recv(65536)
        except TimeoutError as err:
            # Nothing arrived, unless the kernel reports ETIMEDOUT: that is the radio
            # link gone. Python raises the same exception for both, without an errno
            # for its own timeout.
            if err.errno is None:
                return b""
            raise
        if not data:
            raise ConnectionError("Die Gegenstelle hat die Verbindung geschlossen.")
        return data

    def write(self, data: bytes) -> None:
        self._socket.sendall(data)

    def close(self) -> None:
        self._socket.close()


def open_serial(port: str) -> SerialPort:
    import serial

    device = serial.Serial()
    device.port = port
    device.baudrate = 115200
    device.timeout = 0.05
    device.write_timeout = 2
    device.dtr = False
    device.rts = False
    try:
        device.open()
    except serial.SerialException as err:
        log.info("Port %s nicht zu öffnen: %s", port, err)
        raise DeviceError(
            "Das Messgerät lässt sich über USB nicht öffnen. Vielleicht ist ein anderes Programm"
            " damit verbunden."
        ) from err
    return device


def open_channel(port: str) -> Channel:
    """Open `/dev/...` as a serial port, `bt:<address>[/<channel>]` as Bluetooth."""
    if port.startswith("bt:"):
        match = _BLUETOOTH_RE.match(port)
        if not match:
            raise DeviceError(f"Keine gültige Bluetooth-Adresse: {port}")  # a programming error
        return RfcommChannel(match["address"], int(match["channel"] or BLUETOOTH_CHANNEL))
    return SerialChannel(open_serial(port))
