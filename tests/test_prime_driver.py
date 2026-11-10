# EasyMeasurement - tests/test_prime_driver.py
# The PROFITEST PRIME driver against a fake serial port with synthetic replies.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
import threading
from datetime import date, datetime

import pytest

from easymeasurement.devices.base import DeviceError
from easymeasurement.devices.profitest_prime.driver import ProfitestPrimeDriver
from easymeasurement.devices.profitest_prime.transport import (
    READ_ONLY_COMMANDS,
    ForbiddenCommand,
    PrimeTransport,
    SerialChannel,
)

from .prime_helpers import DATABASE


def frame(command: str, data: bytes, error: int = 0, md5: str | None = None) -> bytes:
    digest = md5 if md5 is not None else hashlib.md5(data).hexdigest()
    return (
        f"<reply>\n  <command><![CDATA[{command}]]></command>\n"
        f'  <data type="ASCII"><![CDATA['.encode()
        + data
        + f"]]></data>\n  <md5>{digest}</md5>\n  <error>{error}</error>\n</reply>\n".encode()
    )


class FakePort:
    def __init__(self, replies: dict[str, bytes]):
        self.replies = replies
        self.sent: list[bytes] = []
        self.buffer = b""
        self.closed = False
        self.lock = threading.Lock()

    @property
    def in_waiting(self):
        return len(self.buffer)

    def read(self, size):
        with self.lock:
            chunk, self.buffer = self.buffer[:size], self.buffer[size:]
        return chunk

    def write(self, data):
        self.sent.append(data)
        command = data.decode().strip()
        with self.lock:
            self.buffer = self.replies.get(command, b"")
        return len(data)

    def flush(self):
        pass

    def close(self):
        self.closed = True


def prime_port():
    values = {
        "IDNXML:GET:TYPE": b"PROFITEST PRIME",
        "IDNXML:GET:SERIALNO": b"TEST0001",
        "IDNXML:GET:FIRMWARE": b"01.02.03",
        "IDNXML:GET:HARDWARE": b"A01",
        "IDNXML:GET:ORDERNO": b"M506A",
        "IDNXML:GET:CALIBDATE": b"2026-01-10",
        "IDNXML:GET:RECALIBDATE": b"2027-01-10",
        "IDNXML:DATETIME:GET": b"2026-01-01T09:30:00",
        "DATABASEXML:GET:DATA": DATABASE,
        "PPXML:IS:ON": b"false",
    }
    return FakePort({k: frame(k, v) for k, v in values.items()})


def test_driver_reads_identity_clock_and_measurements():
    port = prime_port()
    with ProfitestPrimeDriver(serial_port=port) as driver:
        identity = driver.identify()
        clock = driver.read_clock()
        measurements = driver.read_measurements()
    assert identity.serial_no == "TEST0001"
    assert identity.recalibration_due == date(2027, 1, 10)
    assert clock == datetime(2026, 1, 1, 9, 30)
    assert len(measurements) == 3
    assert port.closed


@pytest.mark.parametrize(
    "command",
    [
        "DATABASEXML:SET:DATA",
        "DATABASEXML:SET:SEQUENCES",
        "FLASHER:START",
        "LAUNCHER:RUN",
        "SYS:CULTURE:SET:0",
        "FS:VOLUME:FORMAT",
        "FS:FILE:REMOVE",
        "IDNXML:GET:TYPE\nDATABASEXML:SET:DATA",
    ],
)
def test_transport_refuses_anything_off_the_read_list(command):
    port = FakePort({})
    with PrimeTransport(SerialChannel(port)) as transport, pytest.raises(ForbiddenCommand):
        transport.query(command)
    assert port.sent == []


def test_read_list_contains_no_write_verbs():
    for command in READ_ONLY_COMMANDS:
        assert ":SET" not in command
        assert not command.startswith(("FLASHER", "LAUNCHER", "FS:", "SYS:"))


def test_corrupt_reply_is_rejected():
    port = FakePort({"IDNXML:GET:TYPE": frame("IDNXML:GET:TYPE", b"X", md5="0" * 32)})
    with PrimeTransport(SerialChannel(port)) as transport:
        with pytest.raises(DeviceError, match="Prüfsumme"):
            transport.query("IDNXML:GET:TYPE")


def test_busy_port_is_reported_in_plain_words():
    port = FakePort({"IDNXML:GET:TYPE": frame("IDNXML:GET:TYPE", b"", error=402)})
    with PrimeTransport(SerialChannel(port)) as transport:
        with pytest.raises(DeviceError, match="SETUP"):
            transport.query("IDNXML:GET:TYPE")


def test_silent_device_times_out():
    with PrimeTransport(SerialChannel(FakePort({})), timeout_s=0.01) as transport:
        with pytest.raises(DeviceError, match="Keine Antwort"):
            transport.query("IDNXML:GET:TYPE")
