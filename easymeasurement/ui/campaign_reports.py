# EasyMeasurement - easymeasurement/ui/campaign_reports.py
# The reports of the campaign on screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..reporting.language import SOURCE, languages
from .common import ROW_ID, AppContext
from .report_signing import open_report, sign_report


class CampaignReports(QWidget):
    """The protocols of one campaign."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.campaign_id: int | None = None
        self.list = QListWidget()
        self.list.setMinimumHeight(60)
        self.list.currentRowChanged.connect(lambda _: self._update_buttons())
        self.list.itemDoubleClicked.connect(lambda _: self._open())
        self.open_button = QPushButton("Öffnen")
        self.sign_button = QPushButton("Signieren …")
        self.open_button.clicked.connect(self._open)
        self.sign_button.clicked.connect(self._sign)
        actions = QHBoxLayout()
        actions.addWidget(self.open_button)
        actions.addWidget(self.sign_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list, 1)
        layout.addLayout(actions)

    def show_campaign(self, campaign_id: int) -> None:
        self.campaign_id = campaign_id
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        rows = self.app.db.query(
            "SELECT * FROM reports WHERE campaign_id=? ORDER BY created_at DESC, id DESC",
            self.campaign_id,
        )
        for row in rows:
            made = row["created_at"][:16].replace("T", " ")
            mark = "  ·  signiert" if row["signed_by"] else ""
            intact = "" if self.app.archive.is_intact(row) else "  ·  VERÄNDERT ODER FEHLT"
            language = f"  ·  {languages()[row['language']]}" if row["language"] != SOURCE else ""
            item = QListWidgetItem(f"{made}  {row['template_name']}{language}{mark}{intact}")
            item.setData(ROW_ID, row["id"])
            self.list.addItem(item)
        if rows:
            self.list.setCurrentRow(0)
        self._update_buttons()

    def _report(self):
        item = self.list.currentItem()
        return self.app.db.one("SELECT * FROM reports WHERE id=?", item.data(ROW_ID)) if item else None

    def _update_buttons(self) -> None:
        report = self._report()
        self.open_button.setEnabled(report is not None)
        self.sign_button.setEnabled(report is not None and not report["signed_by"])

    def _open(self) -> None:
        report = self._report()
        if report:
            open_report(self.app, report)

    def _sign(self) -> None:
        report = self._report()
        if report and sign_report(self, self.app, report):
            self.refresh()
            self.changed.emit()
