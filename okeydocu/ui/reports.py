# OkeyDocu - okeydocu/ui/reports.py
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

from ..l10n import plural, stored_day, tr
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
        super().__init__(tr("Generate report"), parent)
        self.ok_button.setText(tr("Generate"))
        self.campaign = QComboBox()
        for row in app.service.campaigns():
            if row["status"] == "closed":
                label = f"{row['title']} ({stored_day(row['started_at'])})"
                self.campaign.addItem(label, row["id"])
        self.template = TemplateChoice(app)
        form = QFormLayout()
        form.addRow(tr("Completed campaign"), self.campaign)
        form.addRow(tr("Template"), self.template)
        self.language = LanguageChoice()
        form.addRow(tr("Language"), self.language)
        self.body.addLayout(form)

    def first_field(self):
        return self.campaign


class ReportsPage(QWidget):
    """Every protocol, whichever campaign it belongs to."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.text = QLineEdit(
            placeholderText=tr("Search: customer, installation, campaign, inspector …"))
        self.text.setClearButtonEnabled(True)
        self.signed = QComboBox()
        self.signed.addItem(tr("All reports"), None)
        self.signed.addItem(tr("Signed only"), True)
        self.signed.addItem(tr("Unsigned only"), False)
        self.text.textChanged.connect(self.refresh)
        self.signed.currentIndexChanged.connect(self.refresh)
        top = QHBoxLayout()
        top.addWidget(self.text, 1)
        top.addWidget(self.signed)

        generate = QPushButton(tr("Generate report"))
        self.open_button = QPushButton(tr("Open"))
        self.sign_button = QPushButton(tr("Sign"))
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
            [tr("Created"), tr("Customer"), tr("Installation"), tr("Campaign"), tr("Inspector"),
             tr("Template"), tr("Language"), tr("Signed by"), tr("File")],
            stretch=3,  # the campaign is what a report is looked for by
        )
        self.table.currentCellChanged.connect(lambda *_: self._update_buttons())
        self.table.doubleClicked.connect(self._open)
        self.table.setToolTip(tr("Double-click opens the report"))
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
                tr("unchanged") if intact else tr("CHANGED OR MISSING"),
            ]
            for column, text in enumerate(cells):
                self.table.setItem(index, column, QTableWidgetItem(text))
            self.table.item(index, 0).setData(ROW_ID, row["id"])
        self.count.setText(plural(len(rows), "{count} report", "{count} reports"))
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
            show_error(self, tr("There is no completed campaign yet."))
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
                lambda work: run_busy(self, tr("Creating the report …"), work),
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
