# EasyMeasurement - easymeasurement/ui/instruction_panel.py
# How a measuring function is wired and operated, for measuring without a plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..campaign.plan import load_instructions
from ..l10n import N_, tr
from . import step_text
from .common import function_short
from .wiring_view import WiringView

NO_INSTRUCTION = N_("There are no instructions for this measurement yet.")


class InstructionPanel(QWidget):
    """Follows the last reading and the switch, and any function can be chosen by hand."""

    read_requested = Signal()

    def __init__(self):
        super().__init__()
        self.instructions = load_instructions()
        self.choice = QComboBox()
        for function in sorted(self.instructions, key=function_short):
            self.choice.addItem(function_short(function), function)
        self.choice.currentIndexChanged.connect(lambda _: self._show())
        self.read_button = QPushButton(tr("From the rotary switch"))
        self.read_button.setToolTip(tr("Shows the instructions for the rotary switch position"))
        self.read_button.clicked.connect(self.read_requested)
        self.read_button.hide()
        self.wiring = WiringView()
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.text.setTextFormat(Qt.TextFormat.RichText)
        self.text.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll = QScrollArea()
        scroll.setWidget(self.text)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(280)
        choosing = QHBoxLayout()
        choosing.addWidget(self.choice, 1)
        choosing.addWidget(self.read_button)
        column = QVBoxLayout()
        column.addLayout(choosing)
        column.addWidget(scroll, 1)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.wiring, 1)
        row.addLayout(column)
        self._show()

    def show_function(self, function: str) -> None:
        """Without an instruction the panel says so, it never shows the wrong setup."""
        index = self.choice.findData(function)
        if index >= 0:
            self.choice.setCurrentIndex(index)
            self._show()
        else:
            self.wiring.show_step(None)
            self.text.setText(tr(NO_INSTRUCTION))

    def show_selector(self, position) -> None:
        """A position that names no function leaves the instruction where it is."""
        if position.functions:
            self.show_function(
                min(position.functions, key=lambda key: (key not in self.instructions, key))
            )

    def _show(self) -> None:
        step = self.instructions.get(self.choice.currentData())
        if step is None:
            self.wiring.show_step(None)
            self.text.setText(tr(NO_INSTRUCTION))
            return
        self.wiring.show_step(step if step.wiring else None, connected=True, locked=True)
        parts = (
            step_text.title_html(step), step_text.warnings_html(step),
            step_text.settings_html(step), step_text.instructions_html(step),
            step_text.source_html(step),
        )
        self.text.setText("<br>".join(part for part in parts if part))
