# EasyMeasurement - easymeasurement/ui/plan_test_run.py
# Trying a plan out as the wizard shows it, without leaving any trace.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import tempfile
from pathlib import Path

from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ..campaign.plan import Plan
from ..campaign.service import CampaignService
from ..devices.simulator import SimulatedMeter
from ..reporting.archive import ReportArchive
from ..store import Database
from .common import AppContext
from .guided import GuidedPage
from .instrument_control import InstrumentControl
from .live_session import LiveSession


class PlanTestRun(QWidget):
    """A campaign in a database of its own that ends with this window."""

    def __init__(self, plan: Plan):
        super().__init__()
        self.setWindowTitle(f"Testlauf: {plan.title} – EasyMeasurement")
        self.resize(1000, 640)
        self.folder = tempfile.TemporaryDirectory()
        self.db = Database(":memory:")
        service = CampaignService(self.db, Path(self.folder.name))
        self.app = AppContext(self.db, service, ReportArchive(service))
        customer = self.db.add_customer("Testlauf")
        asset = self.db.add_asset(customer, "installation", "Testanlage")
        meter = SimulatedMeter(failure_rate=0.0)
        self.campaign_id = service.start(asset, plan, "Testlauf", "Testlauf", "simulator", meter)
        self.app.devices.attach(self.campaign_id, meter)
        self.instrument = InstrumentControl(self.app, self)
        self.page = GuidedPage(self.app, self.instrument)
        self.session = LiveSession(meter, self.campaign_id, self)
        self.session.reading.connect(self._received)
        self.instrument.session = self.session
        self.session.start()
        self.page.show_campaign(self.campaign_id)
        self.page.steps.setMaximumWidth(280)
        note = QLabel("Testlauf: Nichts davon wird gespeichert, die Messwerte sind Zufallswerte.")
        row = QHBoxLayout()
        row.addWidget(self.page.steps)
        row.addWidget(self.page, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(note)
        layout.addLayout(row, 1)

    def _received(self, campaign_id: int, reading) -> None:
        self.app.service.receive(campaign_id, reading)
        self.page.show_received(reading)

    def closeEvent(self, event) -> None:
        self.session.stop()
        self.db.close()
        self.folder.cleanup()
        super().closeEvent(event)
