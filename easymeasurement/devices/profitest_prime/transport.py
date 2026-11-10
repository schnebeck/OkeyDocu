# EasyMeasurement - easymeasurement/devices/profitest_prime/transport.py
# Link to the PROFITEST PRIME over USB or Bluetooth: framing and the command list.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
import queue
import re
import threading
import time
from datetime import datetime

from ...l10n import tr
from ..base import DeviceBlocked, DeviceError
from .channels import (  # noqa: F401
    BLUETOOTH_CHANNEL,
    Channel,
    RfcommChannel,
    SerialChannel,
    SerialPort,
    open_channel,
    open_serial,
    socket,
)
from .framing import EVENT, REPLY, TEXT, FrameSplitter  # noqa: F401
from .selector import SELECTOR_COMMAND

# The complete list of what may leave this program. Writes replace instrument
# contents and an unknown command could start a measurement with real test voltage,
# so every command is checked against these lists and there is no way around them.
READ_ONLY_COMMANDS = frozenset(
    {
        "IDNXML:GET:TYPE",
        "IDNXML:GET:FIRMWARE",
        "IDNXML:GET:HARDWARE",
        "IDNXML:GET:SERIALNO",
        "IDNXML:GET:ORDERNO",
        "IDNXML:GET:CALIBDATE",
        "IDNXML:GET:RECALIBDATE",
        "IDNXML:DATETIME:GET",
        "DATABASEXML:GET:DATA",
        "DATABASEXML:GET:TRANSLATIONFILE",  # its words for the TS codes, in every language
    }
)

# These only switch how results are transmitted. The operator still starts every
# measurement on the instrument.
PUSH_COMMANDS = frozenset({"PPXML:IS:ON", "PPXML:ENTER", "PPXML:LEAVE"})

ALLOWED_COMMANDS = READ_ONLY_COMMANDS | PUSH_COMMANDS

# Read commands that exist only in text form, answered with one line and no echo.
TEXT_COMMANDS = frozenset({SELECTOR_COMMAND})

# The only setting that may change, and only through `set_clock`, never `query`.
CLOCK_SET_COMMAND = "IDNXML:DATETIME:SET"

REPLY_TIMEOUT_S = 40.0  # a full database takes about 15 s over Bluetooth
TEXT_TIMEOUT_S = 3.0
BLOCKED_ERROR = 402
_IDLE_S = 0.005

_ECHO_RE = re.compile(rb"<command>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</command>", re.DOTALL)
# Replies without content have an empty <md5 />, and booleans carry no CDATA.
_REPLY_RE = re.compile(
    rb"<data[^>]*?(?:/>|>(?:<!\[CDATA\[(?P<cdata>.*?)\]\]>|(?P<plain>[^<]*))</data>)\s*"
    rb"(?:<md5>(?P<md5>[0-9a-fA-F]*)</md5>|<md5\s*/>)\s*"
    rb"<error>(?P<error>-?\d+)</error>",
    re.DOTALL,
)


class ForbiddenCommand(DeviceError):
    """A command outside the allowed list was about to be sent."""


class LinkLost(DeviceError):
    """The connection to the instrument broke."""


class InstrumentRefused(DeviceError):
    """The instrument answered a command with an error code."""

    def __init__(self, code: int, text: str):
        super().__init__(text)
        self.code = code


class PrimeTransport:
    """Owns the channel. One thread reads; commands run one at a time.

    Replies are matched by their command echo. Events can arrive at any moment
    and wait in `events` as (arrival time, frame) until they are taken.
    """

    def __init__(self, channel: Channel, timeout_s: float = REPLY_TIMEOUT_S):
        self._channel = channel
        self._timeout_s = timeout_s
        self._replies: queue.Queue[bytes | None] = queue.Queue()
        self._lines: queue.Queue[bytes] = queue.Queue()
        self._command_lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.events: queue.Queue[tuple[datetime, bytes]] = queue.Queue()
        self.failure: Exception | None = None

    def __enter__(self) -> "PrimeTransport":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._read_loop, daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._channel.close()

    def _read_loop(self) -> None:
        splitter = FrameSplitter()
        while not self._stop.is_set():
            try:
                data = self._channel.read()
            except OSError as err:
                self.failure = err
                self._replies.put(None)
                return
            if not data:
                time.sleep(_IDLE_S)
                continue
            for kind, frame in splitter.feed(data):
                if kind == EVENT:
                    self.events.put((datetime.now(), frame))
                elif kind == TEXT:
                    self._lines.put(frame)
                else:
                    self._replies.put(frame)

    def query(self, command: str, timeout_s: float | None = None) -> bytes:
        """Send one allowed command and return the verified `data` payload."""
        if command not in ALLOWED_COMMANDS:
            raise ForbiddenCommand(tr("Not on the list of allowed commands: {command}",
                                       command=repr(command)))
        return self._exchange(command, command, timeout_s)

    def query_text(self, command: str, timeout_s: float = TEXT_TIMEOUT_S) -> str:
        """Send one allowed text command and return what follows the code.

        A line has no echo, so one left over from a timed-out command is thrown away first.
        """
        if command not in TEXT_COMMANDS:
            raise ForbiddenCommand(tr("Not on the list of allowed commands: {command}",
                                       command=repr(command)))
        with self._command_lock:
            while not self._lines.empty():
                self._lines.get_nowait()
            self._send(command)
            try:
                line = self._lines.get(timeout=timeout_s)
            except queue.Empty:
                raise DeviceError(tr("No answer to {command}.", command=command)) from None
        code, _, data = line.decode("utf-8", "replace").partition(";")
        if code != "0":
            raise InstrumentRefused(
                int(code),
                tr("The instrument reports error {code} on {command}.", code=code, command=command))
        return data

    def set_clock(self, moment: datetime) -> None:
        """Set date and time in one command. The instrument's clock has no time zone."""
        command = f"{CLOCK_SET_COMMAND} {moment:%Y-%m-%dT%H:%M:%S}"
        self._exchange(command, CLOCK_SET_COMMAND, None)

    def _exchange(self, command: str, echo: str, timeout_s: float | None) -> bytes:
        with self._command_lock:
            self._send(command)
            return self._decode(command, self._await_reply(echo, timeout_s))

    def _send(self, command: str) -> None:
        self.start()
        self._check_link()
        try:
            self._channel.write(command.encode("ascii") + b"\n")
        except OSError as err:
            raise LinkLost(tr("The connection to the instrument broke off.")) from err

    def _check_link(self) -> None:
        if self.failure is not None:
            raise LinkLost(tr("The connection to the instrument broke off."))

    def _await_reply(self, echo_start: str, timeout_s: float | None) -> bytes:
        deadline = time.monotonic() + (self._timeout_s if timeout_s is None else timeout_s)
        while True:
            try:
                frame = self._replies.get(timeout=max(deadline - time.monotonic(), 0))
            except queue.Empty:
                raise DeviceError(tr("No answer to {command}. Is the instrument switched on?",
                                     command=echo_start)) from None
            if frame is None:
                self._replies.put(None)
                self._check_link()
            echo = _ECHO_RE.search(frame)
            # A reply that arrives after its command timed out belongs to nobody.
            if echo and echo[1].strip().decode("ascii", "replace").startswith(echo_start):
                return frame

    @staticmethod
    def _decode(command: str, raw: bytes) -> bytes:
        match = _REPLY_RE.search(raw)
        if not match:
            raise DeviceError(tr("Incomplete answer to {command} ({size} bytes).",
                                    command=command, size=len(raw)))
        error = int(match["error"])
        if error == BLOCKED_ERROR:
            raise DeviceBlocked(tr(
                "The instrument does not release its data right now (error 402). Please turn the"
                " rotary switch to Setup and check whether another program is connected."))
        if error != 0:
            raise InstrumentRefused(error, tr("The instrument reports error {code} on {command}.",
                                              code=error, command=command))
        data = match["cdata"] if match["cdata"] is not None else match["plain"] or b""
        digest = match["md5"]
        if digest and hashlib.md5(data).hexdigest() != digest.decode().lower():
            raise DeviceError(tr("The checksum of the answer to {command} does not match.",
                                command=command))
        return data
