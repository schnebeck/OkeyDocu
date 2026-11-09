# EasyMeasurement - easymeasurement/ui/plan_step_form.py
# The fields of one point of a plan, showing what its kind needs.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QWidget

from ..campaign.plan import load_instructions
from ..model import FUNCTION_LABELS
from .common import function_short
from .growing_edit import GrowingEdit

KIND_TEXT = {"check": "Prüffrage", "measure": "Messung", "note": "Hinweis"}
TITLE_LABELS = {"check": "Frage", "measure": "Titel", "note": "Überschrift"}
TEXT_LABELS = {"check": "Erläuterung", "note": "Text"}


class PlanStepForm(QWidget):
    """Writes into the point it shows, the page around it decides when that is saved."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self.step: dict | None = None
        self.instructions = load_instructions()
        self.heading = QLabel()
        font = self.heading.font()
        font.setBold(True)
        self.heading.setFont(font)
        self.title = QLineEdit()
        self.function = QComboBox()
        for key in sorted(FUNCTION_LABELS, key=function_short):
            self.function.addItem(function_short(key), key)
        self.instruction_state = QLabel()
        self.instruction_state.setWordWrap(True)
        self.text = GrowingEdit()
        self.expected = QComboBox()
        self.expected.addItem("Ja", "yes")
        self.expected.addItem("Nein", "no")
        self.form = QFormLayout(self)
        self.form.addRow(self.heading)
        self.form.addRow("Titel", self.title)
        self.form.addRow("Messfunktion", self.function)
        self.form.addRow("", self.instruction_state)
        self.form.addRow("Text", self.text)
        self.form.addRow("Erwartete Antwort", self.expected)
        self.title.textEdited.connect(self._store)
        self.function.activated.connect(lambda _: self._store())
        self.text.textChanged.connect(self._store)
        self.expected.activated.connect(lambda _: self._store())
        self.show_step(None)

    def _set_row(self, field: QWidget, visible: bool, label: str = "") -> None:
        self.form.setRowVisible(field, visible)
        if label:
            self.form.labelForField(field).setText(label)

    def show_step(self, step: dict | None) -> None:
        self.step = None
        kind = step.get("kind", "measure") if step else ""
        self.heading.setText(KIND_TEXT.get(kind, "Einen Punkt wählen oder hinzufügen."))
        self._set_row(self.title, bool(step), TITLE_LABELS.get(kind, ""))
        self._set_row(self.function, kind == "measure")
        self._set_row(self.instruction_state, kind == "measure")
        self._set_row(self.text, kind in TEXT_LABELS, TEXT_LABELS.get(kind, ""))
        self._set_row(self.expected, kind == "check")
        if step:
            self.title.setText(step.get("title", ""))
            self.function.setCurrentIndex(max(self.function.findData(step.get("function")), 0))
            self.text.blockSignals(True)
            self.text.setPlainText(step.get("text", ""))
            self.text.blockSignals(False)
            self.expected.setCurrentIndex(max(self.expected.findData(step.get("expected")), 0))
            self._show_instruction()
        self.step = step

    def _show_instruction(self) -> None:
        known = self.function.currentData() in self.instructions
        self.instruction_state.setText(
            "Anschlussbild und Anleitung kommen aus der Sammlung." if known
            else "Für diese Funktion gibt es noch keine Anleitung."
        )
        placeholder = self.instructions.get(self.function.currentData())
        self.title.setPlaceholderText(placeholder.title if placeholder else "")

    def _store(self) -> None:
        if self.step is None:
            return
        kind = self.step.get("kind", "measure")
        self.step["title"] = self.title.text().strip()
        if kind == "measure":
            self.step["function"] = self.function.currentData()
            if not self.step["title"]:
                del self.step["title"]
            self._show_instruction()
        else:
            self.step["text"] = self.text.toPlainText().strip()
        if kind == "check":
            self.step["expected"] = self.expected.currentData()
        self.changed.emit()
