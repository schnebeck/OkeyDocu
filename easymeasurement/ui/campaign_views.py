# EasyMeasurement - easymeasurement/ui/campaign_views.py
# The parts of the campaign workspace: its head, the change of tester and the run without a plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QStyle,
    QToolButton,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.service import IMPORTED
from ..devices import Capability
from ..devices.simulator import SIMULATED_FUNCTIONS
from .campaign_list import count_text, heading
from .common import AppContext, function_short
from .instruction_panel import InstructionPanel
from .overlay import Overlay
from .status_badges import BAD, GOOD
from .users import UserChoice

GUIDANCE = {
    GOOD: "<b>Jetzt am Messgerät messen und den Teilen-Knopf drücken.</b>"
          " Jeder Wert erscheint sofort hier und ist gespeichert.",
    BAD: "<b>Das Messgerät ist nicht verbunden.</b>"
         " Ohne Verbindung zeigt es statt Teilen den Speichermanager. Dort speichern oder warten,"
         " die App verbindet sich von selbst.",
}
WAITING_GUIDANCE = "<b>Verbinde mit dem Messgerät …</b>"
MANUAL_GUIDANCE = (
    "<b>Messwerte von Hand eingeben oder Fotos hinzufügen.</b>"
    " Diese Kampagne läuft ohne Messgerät."
)
IMPORT_GUIDANCE = (
    "<b>Importierte Daten prüfen und überarbeiten.</b>"
    " Mit dem Abschluss wird der Datensatz versiegelt, erst dann entsteht das Protokoll."
)


class CampaignHeader(QWidget):
    """Says which campaign this is and offers what can be done with it now."""

    tester_requested = Signal()
    edit_requested = Signal()

    def __init__(self):
        super().__init__()
        self.title = heading("", 15)
        self.edit_button = QToolButton()
        fallback = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.edit_button.setIcon(QIcon.fromTheme("document-edit", fallback))
        self.edit_button.setAccessibleName("Kampagne bearbeiten")
        self.edit_button.setToolTip("Titel und Anlage ändern")
        self.edit_button.setAutoRaise(True)
        self.edit_button.clicked.connect(self.edit_requested)
        self.details = QLabel()
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.linkActivated.connect(lambda _: self.tester_requested.emit())
        self.resume_button = QPushButton("Messung fortsetzen")
        self.pause_button = QPushButton("Messung unterbrechen")
        self.photos_button = QPushButton("Fotos …")
        self.draft_button = QPushButton("Entwurf ansehen")
        self.draft_button.setToolTip("Das Protokoll, wie es jetzt aussähe. Es ist noch nicht gültig.")
        self.finish_button = QPushButton("Bestätigen …")
        self.finish_button.setToolTip("Abschließen, versiegeln, Protokoll ablegen und signieren")
        self.report_button = QPushButton("Protokoll erstellen …")
        text = QVBoxLayout()
        text.setSpacing(0)
        title = QHBoxLayout()
        title.addWidget(self.title)
        title.addWidget(self.edit_button)
        title.addStretch(1)
        text.addLayout(title)
        text.addWidget(self.details)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addLayout(text, 1)
        for button in (self.resume_button, self.pause_button, self.photos_button,
                       self.draft_button, self.finish_button, self.report_button):
            row.addWidget(button)
            # Shown by the campaign that needs them; hidden pages keep their first layout.
            button.hide()


class TesterOverlay(Overlay):
    """The wrong person was chosen, or someone else takes over."""

    def __init__(self, app: AppContext, campaign, count: int, parent=None):
        super().__init__("Prüfer ändern", parent)
        self.ok_button.setText("Übernehmen")
        self.tester = UserChoice(app, campaign["user_id"])
        if campaign["user_id"] is None:  # no linked person: found by the name on record
            self.tester.combo.setCurrentIndex(max(self.tester.combo.findText(campaign["tester"]), 0))
        self.tester.changed.connect(self._update)
        self.measurements = QCheckBox(f"Auch für die bisherigen {count_text(count)}")
        self.measurements.setChecked(count > 0)
        self.measurements.setVisible(count > 0)
        form = QFormLayout()
        form.addRow("Prüfer", self.tester)
        self.body.addLayout(form)
        self.body.addWidget(self.measurements)
        self._update()

    def first_field(self):
        return self.tester.combo

    def _update(self) -> None:
        self.ok_button.setEnabled(self.tester.current_id() is not None)
        self.hint.setText("" if self.ok_button.isEnabled() else "Es fehlt noch ein Prüfer.")


class AssignPlanOverlay(Overlay):
    """Another plan to work through. Its points come after those already there."""

    def __init__(self, plans: list, parent=None):
        super().__init__("Messplan zuweisen", parent)
        self.ok_button.setText("Zuweisen")
        self.plan = QComboBox()
        for plan in plans:
            self.plan.addItem(f"{plan.label} ({len(plan.steps)} Punkte)", plan)
        self.ok_button.setEnabled(bool(plans))
        self.hint.setText("" if plans else "Es gibt noch keinen Messplan.")
        form = QFormLayout()
        form.addRow("Messplan", self.plan)
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
        self.simulate_button = QPushButton("Messung simulieren")
        self.simulate_button.clicked.connect(self.simulate)
        # Help lives in the help menu; the action is there and works while this view shows.
        self.instruction_action = QAction("Anleitung zur Messung", self)
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
        head, end, rest = text.partition("</b>")
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
