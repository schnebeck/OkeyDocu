# EasyMeasurement - easymeasurement/ui/campaign_views.py
# Parts of the campaign workspace: the change of tester, another plan and the run without one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.plan import says_draft
from ..campaign.service import IMPORTED
from ..devices import Capability
from ..devices.simulator import SIMULATED_FUNCTIONS
from ..l10n import N_, tr
from .campaign_items import count_text
from .common import AppContext, function_short
from .instruction_panel import InstructionPanel
from .overlay import Overlay
from .status_badges import BAD, GOOD
from .users import UserChoice

GUIDANCE = {
    GOOD: N_("<b>Now measure on the instrument and press the share key.</b>"
             " Each value appears here at once and is saved."),
    BAD: N_("<b>The instrument is not connected.</b>"
            " Without a connection it shows the memory manager instead of sharing. Save there"
            " or wait, the app connects by itself."),
}
WAITING_GUIDANCE = N_("<b>Connecting to the instrument …</b>")
POINTS = N_("{plan} ({count} points)")
DRAFT_POINTS = N_("{plan} (draft, {count} points)")
MANUAL_GUIDANCE = N_(
    "<b>Enter readings by hand or add photos.</b>"
    " This campaign runs without an instrument."
)
IMPORT_GUIDANCE = N_(
    "<b>Check and revise the imported data.</b>"
    " Completing seals the record, only then is the report created."
)


class TesterOverlay(Overlay):
    """The wrong person was chosen, or someone else takes over."""

    def __init__(self, app: AppContext, campaign, count: int, parent=None):
        super().__init__(tr("Change inspector"), parent)
        self.ok_button.setText(tr("Apply"))
        self.tester = UserChoice(app, campaign["user_id"])
        if campaign["user_id"] is None:  # no linked person: found by the name on record
            self.tester.combo.setCurrentIndex(max(self.tester.combo.findText(campaign["tester"]), 0))
        self.tester.changed.connect(self._update)
        self.measurements = QCheckBox(tr("Also for the previous {measurements}",
                                         measurements=count_text(count)))
        self.measurements.setChecked(count > 0)
        self.measurements.setVisible(count > 0)
        form = QFormLayout()
        form.addRow(tr("Inspector"), self.tester)
        self.body.addLayout(form)
        self.body.addWidget(self.measurements)
        self._update()

    def first_field(self):
        return self.tester.combo

    def _update(self) -> None:
        self.ok_button.setEnabled(self.tester.current_id() is not None)
        missing = not self.ok_button.isEnabled()
        self.hint.setText(tr("An inspector is still missing.") if missing else "")


class AssignPlanOverlay(Overlay):
    """Another plan to work through. Its points come after those already there."""

    def __init__(self, plans: list, parent=None):
        super().__init__(tr("Assign test plan"), parent)
        self.ok_button.setText(tr("Assign"))
        self.plan = QComboBox()
        for plan in plans:
            # A draft says so in the same brackets as its points.
            draft = not plan.released and not says_draft(plan.title)
            shown = DRAFT_POINTS if draft else POINTS
            self.plan.addItem(tr(shown, plan=plan.title, count=len(plan.steps)), plan)
        self.ok_button.setEnabled(bool(plans))
        self.hint.setText("" if plans else tr("There is no test plan yet."))
        form = QFormLayout()
        form.addRow(tr("Test plan"), self.plan)
        self.body.addLayout(form)

    def first_field(self):
        return self.plan


class FreeRunView(QWidget):
    """Measuring without a plan: what to do next, and on request how to wire it."""

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.session = None
        self.driver = None
        self.guidance = QLabel()
        self.guidance.setWordWrap(True)
        self.guidance.setTextFormat(Qt.TextFormat.RichText)
        self.simulate_function = QComboBox()
        for key in SIMULATED_FUNCTIONS:
            self.simulate_function.addItem(function_short(key), key)
        self.simulate_button = QPushButton(tr("Simulate measurement"))
        self.simulate_button.clicked.connect(self.simulate)
        # Help lives in the help menu; the action is there and works while this view shows.
        self.instruction_action = QAction(tr("Measurement instructions"), self)
        self.instruction_action.setCheckable(True)
        self.instruction_action.setShortcut(QKeySequence.StandardKey.HelpContents)
        self.instruction_action.setEnabled(False)
        self.instruction = InstructionPanel()
        self.instruction.setFixedHeight(260)
        self.instruction.hide()
        self.instruction_action.toggled.connect(self._toggle_instruction)
        self.instruction.read_requested.connect(self._read_selector)
        row = QHBoxLayout()
        row.addWidget(self.guidance, 1)
        row.addWidget(self.simulate_function)
        row.addWidget(self.simulate_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row)
        layout.addWidget(self.instruction)

    def show_campaign(self, campaign, session) -> None:
        self.session = session
        self.driver = driver = session.driver if session is not None else None
        simulated = driver is not None and Capability.SIMULATED_TRIGGER in driver.capabilities
        self.instruction.read_button.setVisible(
            driver is not None and Capability.SELECTOR in driver.capabilities
        )
        self.simulate_function.setVisible(simulated)
        self.simulate_button.setVisible(simulated)
        if driver is None:
            self._say(IMPORT_GUIDANCE if campaign["driver"] == IMPORTED else MANUAL_GUIDANCE)

    def _say(self, text: str) -> None:
        """The bold first sentence stays in view, what explains it waits under the mouse."""
        head, end, rest = tr(text).partition("</b>")
        self.guidance.setText(head + end)
        self.guidance.setToolTip(rest.strip())

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.instruction_action.setEnabled(True)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self.instruction_action.setEnabled(False)

    def _toggle_instruction(self, shown: bool) -> None:
        self.instruction.setVisible(shown)
        if shown:
            self._read_selector()

    def _read_selector(self) -> None:
        if self.session is not None:
            self.session.read_selector()

    def show_link(self, kind: str) -> None:
        self._say(GUIDANCE.get(kind, WAITING_GUIDANCE))

    def simulate(self) -> None:
        self.driver.simulate_measurement(self.simulate_function.currentData())
