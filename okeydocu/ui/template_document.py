# OkeyDocu - okeydocu/ui/template_document.py
# The template being edited: load, save, and preview it with invented data.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
from datetime import date, datetime, timedelta

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QInputDialog, QMessageBox

from ..l10n import day, in_language, moment, speaking, tr
from ..model import MeterMeasurement, Quantity, ResultValue, Verdict
from ..reporting.context import ReportMeasurement, ReportStep
from ..reporting.context_texts import company_context
from ..reporting.pdf import render_pdf
from ..reporting.template import TemplateError, parse_template, resolve
from ..reporting.template_model import dump_template
from .common import show_error


def sample_company() -> dict[str, str]:
    """Shown until the own firm is entered, so the letterhead shows where it will stand."""
    return {"name": tr("Own company (Settings → Company)"), "street": tr("Sample street 2"),
            "zip": "12345", "city": tr("Sampletown"), "phone": "", "email": "", "web": "",
            "logo": ""}


def sample_context(count: int) -> dict:
    """Invented data to preview a template with exactly `count` measurements, in the
    language the preview speaks."""
    start = datetime(2026, 1, 15, 9, 0)
    measured = []
    for number in range(count):
        text = f"{2.5 + number * 3.1:.2f}MΩ"
        result = ResultValue("riso", "RISO", Quantity.parse(text), Verdict.PASSED, ">1.00MΩ")
        data = MeterMeasurement(f"m{number}", "riso", start, Verdict.PASSED, results=(result,))
        measured.append(ReportMeasurement(data, start + timedelta(minutes=number)))
    status = "done" if count else "skipped"
    reason = "" if count else tr("Installation not accessible")
    step = ReportStep(in_language("Insulation resistance"), "riso", status, reason, measured)
    return {
        "customer": {"name": tr("Sample customer Ltd"), "street": tr("Sample road 1"),
                     "zip": "12345", "city": tr("Sampletown")},
        "asset": {"name": tr("Sample installation"), "identifier": "A-001",
                  "basis": "DIN VDE 0100-600",
                  "kind_text": tr("Installation"),
                  "features": [(tr("Earthing system type"), "TN-S"),
                               (tr("Rated current"), "63 A")]},
        "campaign": {"title": tr("Preview"), "tester": tr("Max Sample"), "plan": "",
                     "uuid": "preview", "department": tr("Maintenance"),
                     "contact": tr("Ms Example"), "contact_phone": "0123 4567-89",
                     "contact_email": "example@customer.example", "cost_center": "4711",
                     "job_number": "V-2026-0815",
                     "started": moment(start), "closed": moment(start + timedelta(hours=2)),
                     "date": day(start),
                     "clock_offset_s": 0,
                     "clock_summary": tr("set on {moment}", moment=moment(start)),
                     "seal": "0" * 64, "simulated": False},
        "device": {"manufacturer": tr("Example"), "model": tr("Test instrument"),
                   "serial_no": "0001", "firmware": "1.0", "calibrated_on": day(date(2026, 1, 1)),
                   "recalibration_due": day(date(2027, 1, 1)), "overdue": False},
        "steps": [step],
        "report": {"date": day(start.date())},
        "verdict": tr("Passed") if count else tr("Not completely tested"),
    }


class TemplateDocument:
    """Keeps the chosen template, its source text and its preview in step."""

    # Template handling ---------------------------------------------------

    def reload(self) -> None:
        self.refresh_company()
        self.choice.blockSignals(True)
        self.choice.clear()
        for row in self.app.db.templates():
            self.choice.addItem(row["name"], row["body"])
        self.choice.blockSignals(False)
        self._load()

    def _chosen(self) -> None:
        if self.dirty and self._shown_index >= 0 and self._shown_index != self.choice.currentIndex():
            answer = QMessageBox.question(
                self, tr("Template"), tr("The changes are not saved. Discard them?")
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.choice.blockSignals(True)
                self.choice.setCurrentIndex(self._shown_index)
                self.choice.blockSignals(False)
                return
        self._load()

    def _load(self) -> None:
        self._shown_index = self.choice.currentIndex()
        body = self.choice.currentData() or "blocks: []\n"
        try:
            self.template = parse_template(body)
        except TemplateError as err:
            self.message.setText(str(err))
            self.template = {"blocks": []}
        self._fill_tree()
        self._set_source(body)
        self._set_dirty(False)
        self.delete_button.setEnabled(self.choice.count() > 1)
        self.preview()

    def _set_source(self, text: str) -> None:
        self._loading = True
        self.editor.setPlainText(text)
        self._loading = False

    def _set_dirty(self, dirty: bool) -> None:
        self.dirty = dirty
        self.state.setText("geändert" if dirty else "")

    def _touched(self) -> None:
        if self._loading:
            return
        self._set_dirty(True)
        self._debounce.start()

    def _source_edited(self) -> None:
        if not self._loading:
            self._touched()

    def _in_source_mode(self) -> bool:
        return self.modes.currentWidget() is self.editor

    def _mode_changed(self) -> None:
        if self._in_source_mode():
            self._set_source(dump_template(self.template))
            return
        try:
            self.template = parse_template(self.editor.toPlainText())
        except TemplateError as err:
            self.message.setText(str(err))
            self.modes.blockSignals(True)
            self.modes.setCurrentWidget(self.editor)
            self.modes.blockSignals(False)
            return
        self._fill_tree()

    def current_text(self) -> str:
        return self.editor.toPlainText() if self._in_source_mode() else dump_template(self.template)

    def refresh_company(self) -> None:
        """Read once, so drawing the preview never needs the database."""
        company = self.app.db.company()
        self.company = company if company["name"] else None

    def preview(self) -> bool:
        try:
            with speaking(self.preview_language.currentData()):
                company = getattr(self, "company", None) or sample_company()
                values = {**sample_context(self.count.currentData()), **company_context(company)}
                nodes = resolve(parse_template(self.current_text()), values)
                stream = io.BytesIO()
                render_pdf(nodes, stream, footer=tr("Preview with sample data"))
        except TemplateError as err:
            self.message.setText(str(err))
            return False
        self.message.setText("")
        buffer = QBuffer(self)
        buffer.setData(QByteArray(stream.getvalue()))
        buffer.open(QIODevice.OpenModeFlag.ReadOnly)
        self.document.load(buffer)
        self._buffer = buffer
        return True

    def _save(self) -> None:
        if not self.preview():
            show_error(self, tr("The template has errors and was not saved."))
            return
        body = self.current_text()
        self.app.db.save_template(self.choice.currentText(), body)
        self.choice.setItemData(self.choice.currentIndex(), body)
        self.template = parse_template(body)
        self._set_dirty(False)

    def save_as(self, name: str) -> None:
        body = self.current_text()
        self.app.db.save_template(name, body)
        self._set_dirty(False)
        self.choice.blockSignals(True)
        self.choice.clear()
        for row in self.app.db.templates():
            self.choice.addItem(row["name"], row["body"])
        self.choice.setCurrentIndex(self.choice.findText(name))
        self.choice.blockSignals(False)
        self._load()

    def _save_as(self) -> None:
        if not self.preview():
            show_error(self, tr("The template has errors and was not saved."))
            return
        name, accepted = QInputDialog.getText(self, tr("New template"), tr("Name:"))
        if accepted and name.strip():
            self.save_as(name.strip())

    def _delete(self) -> None:
        name = self.choice.currentText()
        answer = QMessageBox.question(
            self, tr("Delete template"),
            tr("Delete “{name}”? Existing reports are not affected.", name=name),
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.app.db.execute("DELETE FROM templates WHERE name=?", name)
            self._set_dirty(False)
            self.reload()
