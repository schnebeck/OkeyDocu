# OkeyDocu - okeydocu/ui/point_edit.py
# Moving and removing a point while a campaign runs on an open template.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QWidget

from ..campaign.templates import OPEN
from ..l10n import tr
from .common import AppContext


def is_open_template(app: AppContext, campaign_id: int) -> bool:
    campaign = app.service.campaign(campaign_id)
    return campaign is not None and campaign["status"] == "open" and \
        app.service.template_mode(campaign["plan_key"]) == OPEN


class PointEdit(QWidget):
    """Shown only where the campaign follows an open template."""

    changed = Signal()

    def __init__(self, app: AppContext, parent=None):
        super().__init__(parent)
        self.app = app
        self.step_id: int | None = None
        self.up = QPushButton(tr("▲ Earlier"))
        self.down = QPushButton(tr("▼ Later"))
        self.remove = QPushButton(tr("Remove point"))
        self.remove.setToolTip(tr("The point leaves this campaign; on confirming, the template"
                                  " can leave it out as well."))
        self.up.clicked.connect(lambda: self._move(-1))
        self.down.clicked.connect(lambda: self._move(1))
        self.remove.clicked.connect(self._remove)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        for button in (self.up, self.down):
            row.addWidget(button)
        row.addStretch(1)
        row.addWidget(self.remove)

    def show_for(self, step_row) -> None:
        self.step_id = step_row["id"]
        self.setVisible(is_open_template(self.app, step_row["campaign_id"]))
        self.remove.setEnabled(step_row["status"] != "done")

    def _move(self, offset: int) -> None:
        self.app.service.move_point(self.step_id, offset)
        self.changed.emit()

    def _remove(self) -> None:
        self.app.service.remove_point(self.step_id)
        self.changed.emit()
