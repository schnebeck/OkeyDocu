# EasyMeasurement - easymeasurement/ui/campaign_edit.py
# What an open campaign is about: its title and installation, with the way to tester and plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton

from ..l10n import N_, tr
from .campaign_dialog import fill_assets
from .common import AppContext
from .overlay import Overlay

TESTER, PLAN = "tester", "plan"
CONTACT_FIELDS = (("department", N_("Department"), N_("e.g. maintenance")),
                  ("contact", N_("Contact person"), N_("e.g. Ms Sample")),
                  ("contact_phone", N_("Extension"), N_("e.g. 0511 1234-56")),
                  ("contact_email", N_("Email"), N_("name@customer.example")))


class CampaignEditOverlay(Overlay):
    """Tester and plan have overlays of their own; their buttons lead there.

    After `exec`, `follow_up` names the overlay to open next, if one was chosen.
    """

    def __init__(self, app: AppContext, campaign, parent=None):
        super().__init__(tr("Edit campaign"), parent)
        self.app = app
        self.campaign = campaign
        self.follow_up = ""
        self.ok_button.setText(tr("Apply"))
        self.title = QLineEdit(campaign["title"])
        self.title.textChanged.connect(lambda _: self._update())
        self.asset = QComboBox()
        fill_assets(self.asset, app)
        self.asset.setCurrentIndex(max(self.asset.findData(campaign["asset_id"]), 0))
        self.asset.currentIndexChanged.connect(lambda _: self._update())
        form = QFormLayout()
        form.addRow(tr("Title"), self.title)
        form.addRow(tr("Installation"), self.asset)
        tester = campaign["tester"] or tr("Inspector missing")
        form.addRow(tr("Inspector"), self._link(tester, tr("Change …"), TESTER))
        plan = campaign["plan_title"] if campaign["plan_key"] else tr("Without test plan")
        form.addRow(tr("Test plan"), self._link(plan, tr("Assign another …"), PLAN))
        # Both sides of the job, named as in the report's letterhead.
        form.addRow(QLabel(tr("<b>Client</b>")))
        self.contact = {}
        for key, label, hint in CONTACT_FIELDS:
            field = QLineEdit(campaign[key])
            field.setPlaceholderText(tr(hint))
            self.contact[key] = field
            form.addRow(tr(label), field)
        form.addRow(QLabel(tr("<b>Contractor</b>")))
        self.cost_center = QLineEdit(campaign["cost_center"])
        self.cost_center.setPlaceholderText(tr("own cost centre for this job"))
        form.addRow(tr("Cost centre"), self.cost_center)
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

    def contact_values(self) -> tuple[str, ...]:
        return tuple(self.contact[key].text().strip() for key, _, _ in CONTACT_FIELDS)

    def _changed(self) -> bool:
        return (self.title.text().strip() != self.campaign["title"]
                or self.asset.currentData() != self.campaign["asset_id"]
                or self.contact_values() != tuple(self.campaign[k] for k, _, _ in CONTACT_FIELDS)
                or self.cost_center.text().strip() != self.campaign["cost_center"])

    def first_field(self):
        return self.title

    def _update(self) -> None:
        problem = ""
        if not self.title.text().strip():
            problem = tr("The title is missing.")
        elif self.asset.currentData() != self.campaign["asset_id"]:
            count = self.app.service.misplaced(self.campaign["id"], self.asset.currentData())
            if count:
                problem = tr("{count} measurements or files belong to parts of the previous"
                             " installation that are not part of this one.", count=count)
        self.hint.setText(problem)
        self.ok_button.setEnabled(not problem)

    def accept(self) -> None:
        if self.ok_button.isEnabled():
            super().accept()
