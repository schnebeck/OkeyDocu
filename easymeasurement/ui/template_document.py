# EasyMeasurement - easymeasurement/ui/template_document.py
# The template being edited: load, save, and preview it with invented data.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
from datetime import datetime, timedelta

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtWidgets import QInputDialog, QMessageBox

from ..model import MeterMeasurement, Quantity, ResultValue, Verdict
from ..reporting.context import ReportMeasurement, ReportStep, company_context
from ..reporting.language import feature_name, kind_name, speaking, tr
from ..reporting.pdf import render_pdf
from ..reporting.template import TemplateError, parse_template, resolve
from ..reporting.template_model import dump_template
from .common import show_error


# Shown until the own firm is entered, so the letterhead shows where it will stand.
SAMPLE_COMPANY = {"name": "Eigene Firma (Einstellungen → Firma)", "street": "Prüferweg 2",
                  "zip": "12345", "city": "Musterstadt", "phone": "", "email": "", "web": "",
                  "logo": ""}


def sample_context(count: int) -> dict:
    """Invented data to preview a template with exactly `count` measurements."""
    start = datetime(2026, 1, 15, 9, 0)
    measured = []
    for number in range(count):
        text = f"{2.5 + number * 3.1:.2f}MΩ"
        result = ResultValue("riso", "RISO", Quantity.parse(text), Verdict.PASSED, ">1.00MΩ")
        data = MeterMeasurement(f"m{number}", "riso", start, Verdict.PASSED, results=(result,))
        measured.append(ReportMeasurement(data, start + timedelta(minutes=number)))
    status = "done" if count else "skipped"
    step = ReportStep("Isolationswiderstand", "riso", status,
                      "" if count else "Anlage nicht zugänglich", measured)
    return {
        "customer": {"name": "Musterkunde GmbH", "street": "Musterweg 1", "zip": "12345",
                     "city": "Musterstadt"},
        "asset": {"name": "Musteranlage", "identifier": "A-001",
                  "kind_text": kind_name("installation", "Anlage"),
                  "features": [(feature_name("netzform", "Netzform"), "TN-S"),
                               (feature_name("nennstrom", "Nennstrom"), "63 A")]},
        "campaign": {"title": "Vorschau", "tester": "Max Muster", "plan": "", "uuid": "vorschau",
                     "started": "15.01.2026 09:00", "closed": "15.01.2026 11:00",
                     "clock_offset_s": 0, "clock_summary": "am 01.01.2026 09:00 gestellt", "seal": "0" * 64, "simulated": False},
        "device": {"manufacturer": "Beispiel", "model": "Messgerät", "serial_no": "0001",
                   "firmware": "1.0", "calibrated_on": "01.01.2026",
                   "recalibration_due": "01.01.2027", "overdue": False},
        "steps": [step],
        "verdict": "Bestanden" if count else "Nicht vollständig geprüft",
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
                self, "Vorlage", "Die Änderungen sind nicht gespeichert. Verwerfen?"
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
                company = getattr(self, "company", None) or SAMPLE_COMPANY
                values = {**sample_context(self.count.currentData()), **company_context(company)}
                nodes = resolve(parse_template(self.current_text()), values)
                stream = io.BytesIO()
                render_pdf(nodes, stream, footer=tr("Vorschau mit Beispieldaten"))
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
            show_error(self, "Die Vorlage enthält Fehler und wurde nicht gespeichert.")
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
            show_error(self, "Die Vorlage enthält Fehler und wurde nicht gespeichert.")
            return
        name, accepted = QInputDialog.getText(self, "Neue Vorlage", "Name:")
        if accepted and name.strip():
            self.save_as(name.strip())

    def _delete(self) -> None:
        name = self.choice.currentText()
        answer = QMessageBox.question(
            self, "Vorlage löschen",
            f"„{name}“ löschen? Bestehende Protokolle bleiben davon unberührt.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.app.db.execute("DELETE FROM templates WHERE name=?", name)
            self._set_dirty(False)
            self.reload()
