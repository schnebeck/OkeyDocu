# OkeyDocu - okeydocu/ui/plan_test_run.py
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

from .. import APP_NAME
from ..campaign.plan import Plan
from ..campaign.service import CampaignService
from ..devices.simulator import SimulatedMeter
from ..l10n import tr
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
        title = tr("Test run: {title}", title=plan.title)
        self.setWindowTitle(f"{title} – {APP_NAME}")
        self.resize(1000, 640)
        self.folder = tempfile.TemporaryDirectory()
        self.db = Database(":memory:")
        service = CampaignService(self.db, Path(self.folder.name))
        self.app = AppContext(self.db, service, ReportArchive(service))
        name = tr("Test run")
        customer = self.db.add_customer(name)
        asset = self.db.add_asset(customer, "installation", tr("Test installation"))
        meter = SimulatedMeter(failure_rate=0.0)
        self.campaign_id = service.start(asset, plan, name, name, "simulator", meter)
        self.app.devices.attach(self.campaign_id, meter)
        self.instrument = InstrumentControl(self.app, self)
        self.page = GuidedPage(self.app, self.instrument)
        self.session = LiveSession(meter, self.campaign_id, self)
        self.session.reading.connect(self._received)
        self.instrument.session = self.session
        self.session.start()
        self.page.show_campaign(self.campaign_id)
        self.page.steps.setMaximumWidth(280)
        note = QLabel(tr("Test run: nothing of this is saved, the readings are random values."))
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
