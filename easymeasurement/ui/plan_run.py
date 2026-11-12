# EasyMeasurement - easymeasurement/ui/plan_run.py
# Working through a test plan: its steps beside the wizard, and a way out of it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Pausing closes the wizard and keeps everything; working on goes on at the first open
step. Ending asks for a reason, which every step still open takes as skipped."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget

from ..l10n import tr
from .guided import GuidedPage


class PlanRun(QWidget):
    paused = Signal()
    end_requested = Signal()
    by_hand_requested = Signal()

    def __init__(self, guided: GuidedPage):
        super().__init__()
        self.guided = guided
        self.title = QLabel()
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        self.pause_button = QPushButton(tr("Pause plan"))
        self.pause_button.setToolTip(tr("Closes the plan; everything stays, and it goes on at"
                                        " the first open step"))
        self.pause_button.clicked.connect(self.paused)
        self.end_button = QPushButton(tr("End plan …"))
        self.end_button.setToolTip(tr("The steps still open count as skipped, with a reason"
                                      " that appears in the report"))
        self.end_button.clicked.connect(self.end_requested)
        self.hand_button = QPushButton(tr("By hand …"))
        self.hand_button.setToolTip(tr("Enters a reading by hand into the step shown"))
        self.hand_button.clicked.connect(self.by_hand_requested)
        bar = QHBoxLayout()
        bar.addWidget(self.title, 1)
        bar.addWidget(self.hand_button)
        bar.addWidget(self.pause_button)
        bar.addWidget(self.end_button)
        split = QSplitter(Qt.Orientation.Horizontal, objectName="plan-run")
        guided.steps.setWordWrap(True)
        guided.steps.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        split.addWidget(guided.steps)
        split.addWidget(guided)
        split.setStretchFactor(1, 1)
        split.setSizes([160, 900])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(bar)
        layout.addWidget(split, 1)

    def show_title(self, title: str) -> None:
        self.title.setText(tr("Test plan: {title}", title=title))
