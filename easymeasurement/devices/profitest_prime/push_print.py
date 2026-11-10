# EasyMeasurement - easymeasurement/devices/profitest_prime/push_print.py
# Push/Print reception for the PROFITEST PRIME driver, with reconnecting.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import atexit
import hashlib
import logging
import queue
import threading
import time
from datetime import datetime
from typing import Callable

from ...l10n import N_, tr
from ...model import UNREADABLE_FUNCTION, MeterMeasurement, Verdict
from ..base import DeviceError, LinkState, LiveReading
from .channels import Channel
from .parser import parse_event
from .transport import InstrumentRefused, PrimeTransport

log = logging.getLogger(__name__)

ACK_TIMEOUT_S = 5.0
PUSH_TIMEOUT_S = 10.0
RECONNECT_DELAY_S = 3.0

PUSH_REFUSALS = {
    403: N_("The instrument is busy elsewhere and accepts no connection."),
    500: N_("Three connections are already signed on at the instrument."
            " Please switch it off and on again."),
}
# Only the connection that signed on can sign off, and a save goes to whoever is signed on.
PUSH_LEFT_ON = N_(
    "The instrument could not be disconnected cleanly. Please switch it off and on again"
    " before measuring without the laptop. Otherwise it may not save measurements."
)


class PushPrintMixin:
    """The Push/Print side of a driver, which provides the attributes listed here."""

    _transport: PrimeTransport | None
    _serial_no: str
    _channel_kind: type | None
    stop_warning: str
    _channel_factory: Callable[[], Channel]
    _reconnect_delay_s: float
    _on_reading: Callable[[LiveReading], None] | None
    _on_state: Callable[[LinkState, str], None] | None
    _pushing: threading.Event
    _dispatcher: threading.Thread | None
    _text: Callable[[str], str]

    def subscribe_live(
        self, on_reading: Callable[[LiveReading], None],
        on_state: Callable[[LinkState, str], None] | None = None,
    ) -> None:
        """Switch on Push/Print. Both callbacks run on a worker thread."""
        if self._transport is None:
            raise DeviceError(tr("The connection to the instrument is not open."))
        if self._pushing.is_set():
            raise DeviceError(tr("Push/Print is already running."))
        if not self._serial_no:
            self._serial_no = self._text("IDNXML:GET:SERIALNO")
        _enter_push(self._transport)
        self._on_reading, self._on_state = on_reading, on_state
        self._pushing.set()
        atexit.register(self.unsubscribe_live)
        self._dispatcher = threading.Thread(target=self._dispatch, daemon=True)
        self._dispatcher.start()

    def unsubscribe_live(self) -> None:
        """Leave Push/Print. Results that have already arrived are still delivered."""
        if not self._pushing.is_set():
            return
        atexit.unregister(self.unsubscribe_live)
        self._pushing.clear()
        transport = self._transport
        if transport is not None:
            try:
                transport.query("PPXML:LEAVE", PUSH_TIMEOUT_S)
            except DeviceError as err:
                log.warning("PPXML:LEAVE failed: %s", err)
                self.stop_warning = tr(PUSH_LEFT_ON)
        if self._dispatcher is not None:
            self._dispatcher.join(timeout=ACK_TIMEOUT_S + 2)
        self._dispatcher = None

    def _dispatch(self) -> None:
        while True:
            transport = self._transport
            if transport is None:
                return
            try:
                received_at, frame = transport.events.get(timeout=0.05)
            except queue.Empty:
                if not self._pushing.is_set():
                    return
                if transport.failure is not None and not self._reconnect(transport):
                    return
                continue
            self._deliver(received_at, frame)
            if self._pushing.is_set():
                self._acknowledge(transport)

    def _deliver(self, received_at: datetime, frame: bytes) -> None:
        reading = LiveReading(_measurement(frame, received_at), received_at)
        try:
            self._on_reading(reading)
        except Exception as err:
            log.exception("Could not hand over a measurement")
            self._report(LinkState.ERROR,
                         tr("The measurement could not be taken over: {error}", error=err))

    @staticmethod
    def _acknowledge(transport: PrimeTransport) -> None:
        """The vendor software sends this after every event; whether it matters is unknown."""
        try:
            transport.query("IDNXML:GET:ORDERNO", ACK_TIMEOUT_S)
        except DeviceError as err:
            log.warning("Acknowledgement failed: %s", err)

    def _report(self, state: LinkState, message: str = "") -> None:
        if self._on_state is None:
            return
        try:
            self._on_state(state, message)
        except Exception:
            log.exception("State report failed")

    def _reconnect(self, lost: PrimeTransport) -> bool:
        self._report(LinkState.LOST, str(lost.failure))
        lost.close()
        while self._pushing.is_set():
            time.sleep(self._reconnect_delay_s)
            transport = None
            try:
                channel = self._channel_factory()
                transport = PrimeTransport(channel)
                serial_no = transport.query("IDNXML:GET:SERIALNO", PUSH_TIMEOUT_S)
                serial_no = serial_no.decode("utf-8", "replace").strip()
                if serial_no != self._serial_no:
                    transport.close()
                    self._pushing.clear()
                    self._report(LinkState.ERROR, tr("A different instrument answered."))
                    return False
                # After a radio dropout the instrument may still be in push mode.
                if transport.query("PPXML:IS:ON", PUSH_TIMEOUT_S).strip() != b"true":
                    _enter_push(transport)
            except (DeviceError, OSError) as err:
                log.info("Reconnecting failed: %s", err)
                if transport is not None:
                    transport.close()
                continue
            if type(channel) is not self._channel_kind:
                self.stop_warning = tr(PUSH_LEFT_ON)
            self._transport = transport
            self._report(LinkState.CONNECTED)
            return True
        return False


def _enter_push(transport: PrimeTransport) -> None:
    try:
        transport.query("PPXML:ENTER", PUSH_TIMEOUT_S)
    except InstrumentRefused as err:
        refusal = PUSH_REFUSALS.get(err.code)
        raise DeviceError(tr(refusal) if refusal else str(err)) from err


def _measurement(frame: bytes, received_at: datetime) -> MeterMeasurement:
    """A record that cannot be parsed is kept as it came: it exists nowhere else."""
    text = frame.decode("utf-8", "replace")
    try:
        measurement = parse_event(frame)
    except (ValueError, SyntaxError) as err:
        log.warning("Unreadable event: %s", err)
        measurement = None
    if measurement is not None:
        return measurement
    return MeterMeasurement(
        uid=hashlib.sha256(frame).hexdigest(), function=UNREADABLE_FUNCTION,
        taken_at=received_at.replace(microsecond=0), verdict=Verdict.NOT_EVALUATED, raw=text,
    )
