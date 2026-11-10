# EasyMeasurement - easymeasurement/ui/reports.py
# Report archive: create, find, open and sign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..reporting.archive import ReportError
from ..reporting.language import languages
from ..reporting.template import TemplateError
from ..store.search import search_reports
from .common import ROW_ID, AppContext, make_table, run_busy, selected_id, show_error
from .confirm_overlay import LanguageChoice, TemplateChoice
from .overlay import Overlay
from .report_signing import open_report, sign_report


class GenerateOverlay(Overlay):
    """A further protocol of a confirmed campaign, for example with another template."""

    def __init__(self, app: AppContext, parent=None):
        super().__init__("Protokoll erzeugen", parent)
        self.ok_button.setText("Erzeugen")
        self.campaign = QComboBox()
        for row in app.service.campaigns():
            if row["status"] == "closed":
                self.campaign.addItem(f"{row['title']} ({row['started_at'][:10]})", row["id"])
        self.template = TemplateChoice(app)
        form = QFormLayout()
        form.addRow("Abgeschlossene Kampagne", self.campaign)
        form.addRow("Vorlage", self.template)
        self.language = LanguageChoice()
        form.addRow("Sprache", self.language)
        self.body.addLayout(form)

    def first_field(self):
        return self.campaign


class ReportsPage(QWidget):
    """Every protocol, whichever campaign it belongs to."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.text = QLineEdit(placeholderText="Suchen: Kunde, Anlage, Kampagne, Prüfer …")
        self.text.setClearButtonEnabled(True)
        self.signed = QComboBox()
        self.signed.addItem("Alle Protokolle", None)
        self.signed.addItem("Nur signierte", True)
        self.signed.addItem("Nur unsignierte", False)
        self.text.textChanged.connect(self.refresh)
        self.signed.currentIndexChanged.connect(self.refresh)
        top = QHBoxLayout()
        top.addWidget(self.text, 1)
        top.addWidget(self.signed)

        generate = QPushButton("Protokoll erzeugen")
        self.open_button = QPushButton("Öffnen")
        self.sign_button = QPushButton("Signieren")
        generate.clicked.connect(lambda: self._generate())
        self.open_button.clicked.connect(self._open)
        self.sign_button.clicked.connect(self._sign)
        self.count = QLabel()
        actions = QHBoxLayout()
        for button in (generate, self.open_button, self.sign_button):
            actions.addWidget(button)
        actions.addStretch()
        actions.addWidget(self.count)

        self.table = make_table(
            ["Erstellt", "Kunde", "Anlage", "Kampagne", "Prüfer", "Vorlage", "Sprache",
             "Signiert von", "Datei"],
            stretch=7,
        )
        self.table.currentCellChanged.connect(lambda *_: self._update_buttons())
        self.table.doubleClicked.connect(self._open)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addLayout(actions)
        layout.addWidget(self.table, 1)
        self.refresh()

    def refresh(self) -> None:
        rows = search_reports(self.app.db, self.text.text(), signed=self.signed.currentData())
        self.table.setRowCount(len(rows))
        for index, row in enumerate(rows):
            intact = self.app.archive.is_intact(row)
            cells = [
                row["created_at"].replace("T", " "), row["customer_name"], row["asset_name"],
                row["campaign_title"], row["tester"], row["template_name"],
                languages().get(row["language"], row["language"]), row["signed_by"],
                "unverändert" if intact else "VERÄNDERT ODER FEHLT",
            ]
            for column, text in enumerate(cells):
                self.table.setItem(index, column, QTableWidgetItem(text))
            self.table.item(index, 0).setData(ROW_ID, row["id"])
        self.count.setText(f"{len(rows)} Protokolle")
        self._update_buttons()

    def _report(self):
        report_id = selected_id(self.table)
        return self.app.db.one("SELECT * FROM reports WHERE id=?", report_id) if report_id else None

    def _update_buttons(self) -> None:
        report = self._report()
        self.open_button.setEnabled(report is not None)
        self.sign_button.setEnabled(report is not None and not report["signed_by"])

    def generate_for(self, campaign_id: int) -> None:
        self._generate(campaign_id)

    def _generate(self, campaign_id: int | None = None) -> None:
        dialog = GenerateOverlay(self.app, self)
        if dialog.campaign.count() == 0:
            show_error(self, "Es gibt noch keine abgeschlossene Kampagne.")
            return
        if campaign_id is not None:
            dialog.campaign.setCurrentIndex(max(dialog.campaign.findData(campaign_id), 0))
        if not dialog.exec():
            return
        try:
            dialog.language.remember()
            self.app.archive.generate(
                dialog.campaign.currentData(), dialog.template.currentText(),
                dialog.template.currentData(), dialog.language.code(),
                lambda work: run_busy(self, "Erstelle das Protokoll …", work),
            )
        except (ReportError, TemplateError) as err:
            show_error(self, str(err))
            return
        self.refresh()
        self.changed.emit()

    def _open(self) -> None:
        report = self._report()
        if report:
            open_report(self.app, report)

    def _sign(self) -> None:
        report = self._report()
        if report and sign_report(self, self.app, report):
            self.refresh()
            self.changed.emit()
