# EasyMeasurement - easymeasurement/ui/instrument_control.py
# What the operator asks of the instrument besides measuring: fetch, check the clock.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtWidgets import QInputDialog, QWidget

from ..campaign.service import clock_needs_setting, measure_clock_offset, set_instrument_clock
from ..devices import DeviceError
from .common import AppContext, ask_clock_sync, run_busy, show_error


class InstrumentControl:
    def __init__(self, app: AppContext, owner: QWidget):
        self.app = app
        self.owner = owner
        self.session = None  # the live session holding the instrument, if any

    @contextmanager
    def free(self):
        """The connection is exclusive, so the live session steps aside."""
        session = self.session
        if session is not None:
            run_busy(self.owner, "Trenne vom Messgerät …", session.stop)
        try:
            yield
        finally:
            if session is not None:
                session.start()

    def fetch(self, campaign_id: int) -> dict | None:
        """What is stored on the instrument. None if it could not be reached."""
        driver = self.app.devices.driver(self.app.service.campaign(campaign_id))

        def read():
            with driver:
                return driver.read_measurements()

        try:
            with self.free():
                stored = run_busy(self.owner, "Rufe die Messwerte vom Gerät ab …", read)
        except DeviceError as err:
            show_error(self.owner, str(err))
            return None
        return self.app.service.file_measurements(campaign_id, stored)

    def check_clock(self, campaign_id: int) -> float | None:
        """The offset that remains. None if the instrument could not be reached."""
        driver = self.app.devices.driver(self.app.service.campaign(campaign_id))

        def measure():
            with driver:
                return measure_clock_offset(driver)

        def fetch_and_set():
            # What is still on the instrument carries its old time, so it comes first.
            with driver:
                return driver.read_measurements(), set_instrument_clock(driver)

        try:
            with self.free():
                offset = run_busy(self.owner, "Prüfe die Geräteuhr …", measure)
                self.app.service.record_clock_check(campaign_id, offset)
                if clock_needs_setting(offset, driver) and ask_clock_sync(self.owner, offset):
                    stored, before = run_busy(self.owner, "Stelle die Geräteuhr …", fetch_and_set)
                    self.app.service.file_measurements(campaign_id, stored)
                    self.app.service.record_clock_set(campaign_id, before)
                    offset = 0.0
        except DeviceError as err:
            show_error(self.owner, str(err))
            return None
        return offset

    def correct_clock(self, campaign_id: int) -> bool:
        campaign = self.app.service.campaign(campaign_id)
        offset, accepted = QInputDialog.getInt(
            self.owner, "Uhrenversatz", "Das Messgerät geht vor (+) oder nach (−), in Sekunden:",
            round(campaign["clock_offset_s"]), -86400, 86400,
        )
        if not accepted:
            return False
        try:
            self.app.service.correct_clock_offset(campaign_id, offset)
        except DeviceError as err:
            show_error(self.owner, str(err))
            return False
        return True
