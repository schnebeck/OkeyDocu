# EasyMeasurement - easymeasurement/ui/campaign_edit.py
# What an open campaign is about: its title and installation, with the way to tester and plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

from .campaign_dialog import fill_assets
from .common import AppContext
from .overlay import Overlay

TESTER, PLAN = "tester", "plan"


class CampaignEditOverlay(Overlay):
    """Tester and plan have overlays of their own; their buttons lead there.

    After `exec`, `follow_up` names the overlay to open next, if one was chosen.
    """

    def __init__(self, app: AppContext, campaign, parent=None):
        super().__init__("Kampagne bearbeiten", parent)
        self.app = app
        self.campaign = campaign
        self.follow_up = ""
        self.ok_button.setText("Übernehmen")
        self.title = QLineEdit(campaign["title"])
        self.title.textChanged.connect(lambda _: self._update())
        self.asset = QComboBox()
        fill_assets(self.asset, app)
        self.asset.setCurrentIndex(max(self.asset.findData(campaign["asset_id"]), 0))
        self.asset.currentIndexChanged.connect(lambda _: self._update())
        form = QFormLayout()
        form.addRow("Titel", self.title)
        form.addRow("Anlage", self.asset)
        form.addRow("Prüfer", self._link(campaign["tester"] or "Prüfer fehlt", "Ändern …", TESTER))
        plan = campaign["plan_title"] if campaign["plan_key"] else "Ohne Messplan"
        form.addRow("Messplan", self._link(plan, "Weiteren zuweisen …", PLAN))
        self.body.addLayout(form)
        self._update()

    def _link(self, text: str, button_text: str, follow_up: str) -> QHBoxLayout:
        label = QLabel(text)
        label.setWordWrap(True)
        button = QPushButton(button_text)
        button.clicked.connect(lambda: self._follow(follow_up))
        row = QHBoxLayout()
        row.addWidget(label, 1)
        row.addWidget(button)
        return row

    def _follow(self, follow_up: str) -> None:
        """Keeps what was typed, where it may be kept, and moves on."""
        self.follow_up = follow_up
        if self._changed() and self.ok_button.isEnabled():
            self.accept()
        else:
            self.reject()

    def _changed(self) -> bool:
        return (self.title.text().strip() != self.campaign["title"]
                or self.asset.currentData() != self.campaign["asset_id"])

    def first_field(self):
        return self.title

    def _update(self) -> None:
        problem = ""
        if not self.title.text().strip():
            problem = "Der Titel fehlt."
        elif self.asset.currentData() != self.campaign["asset_id"]:
            count = self.app.service.misplaced(self.campaign["id"], self.asset.currentData())
            if count:
                problem = (f"{count} Messungen oder Dateien hängen an Teilen der bisherigen Anlage,"
                           " die nicht zu dieser gehören.")
        self.hint.setText(problem)
        self.ok_button.setEnabled(not problem)

    def accept(self) -> None:
        if self.ok_button.isEnabled():
            super().accept()
