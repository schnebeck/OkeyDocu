# EasyMeasurement - easymeasurement/ui/live_session.py
# Keeps the instrument connected while a campaign is open and hands results to the GUI.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import logging
import threading

from PySide6.QtCore import QObject, Signal

from ..devices import Capability, DeviceError, LinkState, MeterDriver
from ..l10n import N_, tr
from .status_badges import BAD, GOOD, WAITING

log = logging.getLogger(__name__)

RETRY_S = 5.0
CONNECTED_TEXT = N_("Instrument connected")
CONNECTING_TEXT = N_("Connecting to the instrument …")
LOST_TEXT = N_("Instrument not connected")


class LiveSession(QObject):
    """Signals may come from worker threads; Qt delivers them on the GUI thread.

    A reading names its campaign: the window may show another one by the time it
    arrives, and a reading still on its way must not end up in the wrong record.
    """

    reading = Signal(int, object)
    link = Signal(str, str)
    selector = Signal(object)

    def __init__(self, driver: MeterDriver, campaign_id: int = 0, parent=None):
        super().__init__(parent)
        self.driver = driver
        self.campaign_id = campaign_id
        self._stop = threading.Event()
        # Without a link the operator can only store on the instrument, so readings may lie
        # there with the clock as it was. Set on any loss, never cleared for this session.
        self.gap = False
        self._thread: threading.Thread | None = None
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        self._stop.clear()
        self.link.emit(WAITING, tr(CONNECTING_TEXT))
        if Capability.SIMULATED_TRIGGER in self.driver.capabilities:
            self._connect()
        else:
            self._thread = threading.Thread(target=self._keep_trying, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Leaves Push/Print. Can take seconds with a real instrument."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join()
            self._thread = None
        if self._reader is not None:
            self._reader.join()
            self._reader = None
        self.driver.close()

    def read_selector(self) -> None:
        """Answers through `selector`, and not at all if the instrument cannot tell."""
        capabilities = self.driver.capabilities
        if Capability.SIMULATED_TRIGGER in capabilities:
            self._read_selector()
        elif Capability.SELECTOR in capabilities:
            self._reader = threading.Thread(target=self._read_selector, daemon=True)
            self._reader.start()

    def _read_selector(self) -> None:
        try:
            self.selector.emit(self.driver.read_selector())
        except DeviceError as err:
            log.info("Selector not readable: %s", err)

    def _keep_trying(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect()
                return
            except DeviceError as err:
                log.info("Instrument not reachable: %s", err)
                self.driver.close()
                self.gap = True
                self.link.emit(BAD, tr(LOST_TEXT))
            self._stop.wait(RETRY_S)

    def _connect(self) -> None:
        self.driver.open()
        self.driver.subscribe_live(self._on_reading, self._on_state)
        self.link.emit(GOOD, tr(CONNECTED_TEXT))

    def _on_reading(self, reading) -> None:
        self.reading.emit(self.campaign_id, reading)

    def _on_state(self, state: LinkState, text: str) -> None:
        if state is not LinkState.CONNECTED and not self._stop.is_set():
            self.gap = True  # a stop asked for here is no loss
        if state is LinkState.CONNECTED:
            self.link.emit(GOOD, tr(CONNECTED_TEXT))
        elif state is LinkState.LOST:
            self.link.emit(BAD, tr(LOST_TEXT))
        else:
            self.link.emit(BAD, text)
