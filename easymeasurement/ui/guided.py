# EasyMeasurement - easymeasurement/ui/guided.py
# The guided campaign: show the setup, confirm it, measure, collect, next step.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..campaign.plan import says_draft
from ..devices import is_simulated
from ..devices.simulator import SIMULATED_FUNCTIONS
from ..l10n import day, tr
from .common import AppContext, function_short, make_table
from .guided_actions import GuidedActions
from .guided_pages import CheckPage, NotePage
from .guided_steps import GuidedSteps
from .instrument_control import InstrumentControl
from .wiring_view import WiringView


def _label(wrap: bool = True) -> QLabel:
    label = QLabel()
    label.setWordWrap(wrap)
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


class GuidedPage(GuidedSteps, GuidedActions, QWidget):
    """A wizard: one point at a time, with its place in the plan always in sight.

    The list of points stands beside the measurements, not in here.
    """

    changed = Signal()
    started = Signal(int)
    step_shown = Signal(object)
    loose_counted = Signal(int)

    def __init__(self, app: AppContext, instrument: InstrumentControl):
        super().__init__()
        self.app = app
        self.campaign_id: int | None = None
        self.instrument = instrument

        self.banner = _label()

        self.steps = QListWidget()
        self.steps.currentRowChanged.connect(lambda _: self._show_step())

        self.wiring = WiringView()
        self.wiring.progress.connect(self._wiring_progress)
        self.wiring_hint = QLabel()
        centre = QWidget()
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.addWidget(self.wiring, 1)
        centre_layout.addWidget(self.wiring_hint)

        self.step_title = _label()
        self.settings_text = _label()
        self.warnings_text = _label()
        self.instructions_text = _label()
        self.source_text = _label()
        self.device_set = QCheckBox(tr("Rotary switch and settings are set as given"))
        self.device_set.toggled.connect(self._update_actions)
        self.device_set.clicked.connect(lambda ticked: ticked and self._read_selector())
        self.selector_hint = _label()
        self.confirm_button = QPushButton(tr("Confirm setup"))
        self.confirm_button.clicked.connect(self.confirm)
        inner = QWidget()
        side = QVBoxLayout(inner)
        for widget in (self.step_title, self.warnings_text, self.settings_text,
                       self.instructions_text, self.source_text):
            side.addWidget(widget)
        side.addStretch()
        side.addWidget(self.selector_hint)
        side.addWidget(self.device_set)
        side.addWidget(self.confirm_button)
        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(320)

        upper = QSplitter(objectName="guided-step")
        for widget in (centre, scroll):
            upper.addWidget(widget)
        upper.setStretchFactor(0, 1)

        self.simulate_function = QComboBox()
        for key in SIMULATED_FUNCTIONS:
            self.simulate_function.addItem(function_short(key), key)
        self.simulate_button = QPushButton(tr("Simulate measurement"))
        self.fetch_button = QPushButton(tr("Fetch from the instrument"))
        self.skip_button = QPushButton(tr("Skip step …"))
        self.simulate_button.clicked.connect(self.simulate)
        self.fetch_button.clicked.connect(self.fetch)
        self.skip_button.clicked.connect(self._skip)
        self.status = QLabel()
        actions = QHBoxLayout()
        for widget in (self.simulate_function, self.simulate_button, self.fetch_button,
                       self.skip_button):
            actions.addWidget(widget)
        actions.addStretch()
        actions.addWidget(self.status)
        self.measure_page = QWidget()
        measure_layout = QVBoxLayout(self.measure_page)
        measure_layout.setContentsMargins(0, 0, 0, 0)
        measure_layout.addWidget(upper, 1)
        measure_layout.addLayout(actions)

        self.check_page = CheckPage()
        self.check_page.chosen.connect(self._check_chosen)
        self.check_page.edited.connect(self._check_edited)
        self.check_page.next_requested.connect(self._next_if_ready)
        self.note_page = NotePage()
        self.pages = QStackedWidget()
        for page in (self.measure_page, self.check_page, self.note_page):
            self.pages.addWidget(page)

        self.position = QLabel()
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setMaximumHeight(6)
        self.back_button = QPushButton(tr("← Back"))
        self.next_button = QPushButton(tr("Next →"))
        self.next_button.setDefault(True)
        self.back_button.clicked.connect(self.previous)
        self.next_button.clicked.connect(self.next_point)
        navigation = QHBoxLayout()
        navigation.addWidget(self.position, 1)
        navigation.addWidget(self.back_button)
        navigation.addWidget(self.next_button)

        columns = [tr("Time"), tr("Designation"), tr("Readings"), tr("Reason")]
        self.open_table = make_table(columns, 2)
        self.assign_button = QPushButton(tr("Assign to the chosen step"))
        self.assign_button.clicked.connect(self._assign_open)
        self.open_box = QWidget()
        open_layout = QVBoxLayout(self.open_box)
        open_layout.setContentsMargins(0, 0, 0, 0)
        open_layout.addWidget(self.open_table)
        open_layout.addWidget(self.assign_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.banner)
        layout.addWidget(self.progress)
        layout.addWidget(self.pages, 1)
        layout.addLayout(navigation)
        self.reload()

    # Campaigns -----------------------------------------------------------

    @property
    def plans(self):
        return self.app.service.plans()

    def reload(self) -> None:
        self._fill_steps()

    def show_campaign(self, campaign_id: int | None) -> None:
        self.campaign_id = campaign_id
        self.steps.clear()
        self.reload()

    def show_received(self, reading) -> None:
        results = reading.measurement.results[:2]
        text = "   ".join(f"{r.label} {r.quantity.raw}" for r in results)
        self.status.setText(tr("Received: {values}", values=text))
        self._fill_steps()

    def _campaign(self):
        return self.app.service.campaign(self.campaign_id) if self.campaign_id else None

    def _update_banner(self) -> None:
        campaign = self._campaign()
        if campaign is None:
            self.banner.hide()
            return
        notes = []
        if says_draft(campaign["plan_title"]):
            notes.append(tr("The test plan is a draft and not yet approved technically."))
        if is_simulated(campaign["driver"]):
            notes.append(tr("<b>Simulation:</b> The readings are random values."))
        identity = self.app.service.identity(self.campaign_id)
        if identity.calibration_overdue(datetime.now().date()):
            notes.append(tr("<b>Recalibration overdue since {day}.</b>",
                            day=day(identity.recalibration_due)))
        self.banner.setText(" · ".join(notes))
        self.banner.setVisible(bool(notes))
