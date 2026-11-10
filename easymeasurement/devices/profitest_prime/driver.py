# EasyMeasurement - easymeasurement/devices/profitest_prime/driver.py
# MeterDriver implementation for the PROFITEST PRIME over USB and Bluetooth.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Callable

from ...l10n import tr
from ...model import DeviceIdentity, MeterMeasurement
from ..base import Capability, DeviceError, DeviceTexts, LinkState, LiveReading, MeterDriver
from ..base import SelectorPosition
from .channels import Channel, SerialChannel, SerialPort, open_channel
from .discovery import open_any
from .parser import parse_database, parse_date
from .push_print import PUSH_TIMEOUT_S, RECONNECT_DELAY_S, PushPrintMixin
from .selector import SELECTOR_COMMAND, selector_position
from .texts import TEXTS_COMMAND, TEXTS_TIMEOUT_S, parse_texts
from .transport import PrimeTransport

log = logging.getLogger(__name__)


class ProfitestPrimeDriver(PushPrintMixin, MeterDriver):
    """Identity, clock, stored measurements and Push/Print.

    With Push/Print on, the instrument sends each measurement when the operator
    presses save. A pushed measurement is not kept on the instrument, so the
    receiver holds the only copy: it reaches the callback before anything else
    happens to it, and a record that cannot be parsed is delivered unparsed.

    Stored measurements are fetched on request, not polled. The instrument only
    releases them with the rotary switch on Setup.
    """

    capabilities = (
        Capability.READ_STORED | Capability.CLOCK | Capability.SET_CLOCK
        | Capability.LIVE_RESULTS | Capability.SELECTOR | Capability.TEXTS
    )

    def __init__(
        self, port: str = "", serial_port: SerialPort | None = None,
        channel_factory: Callable[[], Channel] | None = None,
        reconnect_delay_s: float = RECONNECT_DELAY_S,
    ):
        if channel_factory is None:
            if serial_port is not None:
                channel_factory = lambda: SerialChannel(serial_port)  # noqa: E731
            else:
                channel_factory = (lambda: open_channel(port)) if port else open_any
        self._channel_factory = channel_factory
        self._reconnect_delay_s = reconnect_delay_s
        self._transport: PrimeTransport | None = None
        self._channel_kind: type | None = None
        self._serial_no = ""
        self._on_reading: Callable[[LiveReading], None] | None = None
        self._on_state: Callable[[LinkState, str], None] | None = None
        self._pushing = threading.Event()
        self._dispatcher: threading.Thread | None = None

    def open(self) -> None:
        channel = self._channel_factory()
        self._channel_kind = type(channel)
        self._transport = PrimeTransport(channel)
        try:
            self._leave_stale_push(self._transport)
        except DeviceError:
            self._transport.close()
            self._transport = None
            raise

    def close(self) -> None:
        self.unsubscribe_live()
        if self._transport is not None:
            self._transport.close()
        self._transport = None

    @staticmethod
    def _leave_stale_push(transport: PrimeTransport) -> None:
        """A crash can leave the instrument in push mode."""
        if transport.query("PPXML:IS:ON", PUSH_TIMEOUT_S).strip() == b"true":
            transport.query("PPXML:LEAVE", PUSH_TIMEOUT_S)

    def _query(self, command: str) -> bytes:
        if self._transport is None:
            raise DeviceError(tr("The connection to the instrument is not open."))
        return self._transport.query(command)

    def _text(self, command: str) -> str:
        return self._query(command).decode("utf-8", errors="replace").strip()

    def identify(self) -> DeviceIdentity:
        identity = DeviceIdentity(
            manufacturer="GOSSEN METRAWATT",
            model=self._text("IDNXML:GET:TYPE"),
            serial_no=self._text("IDNXML:GET:SERIALNO"),
            firmware=self._text("IDNXML:GET:FIRMWARE"),
            hardware=self._text("IDNXML:GET:HARDWARE"),
            order_no=self._text("IDNXML:GET:ORDERNO"),
            calibrated_on=parse_date(self._text("IDNXML:GET:CALIBDATE")),
            recalibration_due=parse_date(self._text("IDNXML:GET:RECALIBDATE")),
        )
        self._serial_no = identity.serial_no
        return identity

    def read_clock(self) -> datetime:
        clock = datetime.fromisoformat(self._text("IDNXML:DATETIME:GET"))
        if clock.tzinfo is not None:
            clock = clock.astimezone().replace(tzinfo=None)
        return clock.replace(microsecond=0)

    def sync_clock(self) -> None:
        if self._transport is None:
            raise DeviceError(tr("The connection to the instrument is not open."))
        if self._pushing.is_set():
            raise DeviceError(tr("The clock cannot be set during Push/Print."))
        # The instrument counts whole seconds, so start on one.
        time.sleep(1 - datetime.now().microsecond / 1e6)
        self._transport.set_clock(datetime.now())

    def read_selector(self) -> SelectorPosition:
        """Read on request only.

        The instrument writes an event in pieces and nothing keeps a reply out of it, so
        a steady stream of questions could land inside a measurement being pushed.
        """
        transport = self._transport
        if transport is None:
            raise DeviceError(tr("The connection to the instrument is not open."))
        text = transport.query_text(SELECTOR_COMMAND)
        log.info("Selector position %s", text)
        try:
            return selector_position(int(text))
        except ValueError:
            raise DeviceError(tr("Unexpected switch position: {text}", text=repr(text))) from None

    def read_texts(self) -> DeviceTexts:
        if self._transport is None:
            raise DeviceError(tr("The connection to the instrument is not open."))
        return parse_texts(self._transport.query(TEXTS_COMMAND, TEXTS_TIMEOUT_S))

    def read_measurements(self) -> list[MeterMeasurement]:
        return parse_database(self._query("DATABASEXML:GET:DATA"))[1]
