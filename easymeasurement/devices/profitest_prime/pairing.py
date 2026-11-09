# EasyMeasurement - easymeasurement/devices/profitest_prime/pairing.py
# First-time Bluetooth pairing through BlueZ. Needed once per instrument.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import os
import pty
import re
import select
import subprocess
import time
from typing import Callable

from ..base import DeviceError
from .discovery import BLUETOOTH_NAME

DEFAULT_PIN = "1234"  # factory setting of the instrument
SCAN_TIMEOUT_S = 30.0
PAIR_TIMEOUT_S = 45.0

_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]|\x01|\x02")
_FOUND_RE = re.compile(
    rf"\[NEW\] Device (?P<address>(?:[0-9A-F]{{2}}:){{5}}[0-9A-F]{{2}}) {BLUETOOTH_NAME}", re.I
)


class PairingFailed(DeviceError):
    pass


class _Session:
    """Talks to bluetoothctl as a person would: it has an agent for the PIN."""

    def __init__(self, command: list[str]):
        # Not pty.fork(): this runs on a worker thread, and forking there is unsafe.
        self.fd, terminal = pty.openpty()
        try:
            self.process = subprocess.Popen(
                command, stdin=terminal, stdout=terminal, stderr=terminal, start_new_session=True
            )
        except OSError:
            os.close(self.fd)
            raise
        finally:
            os.close(terminal)
        self.seen = ""
        self.position = 0

    def send(self, text: str) -> None:
        os.write(self.fd, text.encode() + b"\n")

    def poll(self, seconds: float = 0.2) -> str:
        """Return what is new since the last look."""
        ready, _, _ = select.select([self.fd], [], [], seconds)
        if ready:
            try:
                self.seen += _ANSI_RE.sub("", os.read(self.fd, 4096).decode("utf-8", "replace"))
            except OSError:
                raise PairingFailed("Die Bluetooth-Werkzeuge wurden unerwartet beendet.") from None
        new, self.position = self.seen[self.position:], len(self.seen)
        return new

    def close(self) -> None:
        try:
            self.send("quit")
            time.sleep(0.2)
        except OSError:
            pass
        os.close(self.fd)
        self.process.terminate()
        self.process.wait()


def _wait_for_instrument(session: _Session, timeout_s: float) -> str:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        session.poll()
        match = _FOUND_RE.search(session.seen)
        if match:
            return match["address"]
    raise PairingFailed(
        "Das Messgerät wurde nicht gefunden. Bitte Drehschalter auf SETUP stellen und im"
        " Bluetooth-Menü Bluetooth einschalten und sichtbar stellen."
    )


def _pair(session: _Session, address: str, pin: str, timeout_s: float) -> None:
    session.send(f"pair {address}")
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        new = session.poll()
        if re.search(r"Enter PIN code|Enter passkey", new):
            session.send(pin)
        elif re.search(r"Confirm passkey|\(yes/no\)", new):
            session.send("yes")
        if "Pairing successful" in session.seen or "AlreadyExists" in session.seen:
            return
        if "Failed to pair" in session.seen:
            raise PairingFailed(
                "Die Kopplung ist fehlgeschlagen. Bitte die PIN prüfen und am Messgerät unter"
                " „Vertraute Geräte“ eine alte Kopplung löschen."
            )
    raise PairingFailed("Die Kopplung hat nicht rechtzeitig geantwortet.")


def pair_instrument(
    pin: str = DEFAULT_PIN, on_progress: Callable[[str], None] = lambda text: None,
    command: tuple[str, ...] = ("bluetoothctl",), scan_timeout_s: float = SCAN_TIMEOUT_S,
    pair_timeout_s: float = PAIR_TIMEOUT_S,
) -> str:
    """Find a visible instrument, pair and trust it. Returns its address."""
    try:
        session = _Session(list(command))
    except OSError as err:
        raise PairingFailed(f"Bluetooth ist nicht verfügbar: {err}") from err
    try:
        for line in ("power on", "pairable on", "agent KeyboardDisplay", "default-agent", "scan on"):
            session.send(line)
            time.sleep(0.2)
        on_progress("Suche das Messgerät …")
        address = _wait_for_instrument(session, scan_timeout_s)
        session.send("scan off")
        time.sleep(0.5)
        on_progress("Messgerät gefunden, kopple …")
        _pair(session, address, pin, pair_timeout_s)
        session.send(f"trust {address}")
        time.sleep(0.5)
        return address
    finally:
        session.close()
