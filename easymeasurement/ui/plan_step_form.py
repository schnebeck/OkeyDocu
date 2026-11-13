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
from ..l10n import N_, in_language, tr
from ..vocabulary import function_keys
from .common import function_short
from .growing_edit import GrowingEdit

KIND_TEXT = {"check": N_("Check question"), "measure": N_("Measurement"), "note": N_("Hint")}
TITLE_LABELS = {"check": N_("Question"), "measure": N_("Title"), "note": N_("Heading")}
TEXT_LABELS = {"check": N_("Explanation"), "note": N_("Text")}


def kept(stored: str, typed: str) -> str:
    """A shipped text is shown in the current language; left as shown, it stays in the
    language it is kept in, so every other language still finds its translation."""
    return stored if typed == in_language(stored) else typed


class PlanStepForm(QWidget):
    """Writes into the point it shows, the page around it decides when that is saved."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self.step: dict | None = None
        self.stored: dict[str, str] = {}  # the texts as kept, before the language shows them
        self.instructions = load_instructions()
        self.heading = QLabel()
        font = self.heading.font()
        font.setBold(True)
        self.heading.setFont(font)
        self.title = QLineEdit()
        self.function = QComboBox()
        for key in sorted(function_keys(), key=function_short):
            self.function.addItem(function_short(key), key)
        self.instruction_state = QLabel()
        self.instruction_state.setWordWrap(True)
        self.text = GrowingEdit()
        self.expected = QComboBox()
        self.expected.addItem(tr("Yes"), "yes")
        self.expected.addItem(tr("No"), "no")
        self.form = QFormLayout(self)
        self.form.addRow(self.heading)
        self.form.addRow(tr("Title"), self.title)
        self.form.addRow(tr("Measured quantity"), self.function)
        self.form.addRow("", self.instruction_state)
        self.form.addRow(tr("Text"), self.text)
        self.form.addRow(tr("Expected answer"), self.expected)
        self.title.textEdited.connect(self._store)
        self.function.activated.connect(lambda _: self._store())
        self.text.textChanged.connect(self._store)
        self.expected.activated.connect(lambda _: self._store())
        self.show_step(None)

    def _set_row(self, field: QWidget, visible: bool, label: str = "") -> None:
        self.form.setRowVisible(field, visible)
        if label:
            self.form.labelForField(field).setText(tr(label))

    def show_step(self, step: dict | None) -> None:
        self.step = None
        kind = step.get("kind", "measure") if step else ""
        self.heading.setText(tr(KIND_TEXT.get(kind, N_("Choose or add a point."))))
        self._set_row(self.title, bool(step), TITLE_LABELS.get(kind, ""))
        self._set_row(self.function, kind == "measure")
        self._set_row(self.instruction_state, kind == "measure")
        self._set_row(self.text, kind in TEXT_LABELS, TEXT_LABELS.get(kind, ""))
        self._set_row(self.expected, kind == "check")
        self.stored = {key: step.get(key, "") for key in ("title", "text")} if step else {}
        if step:
            self.title.setText(in_language(self.stored["title"]))
            self.function.setCurrentIndex(max(self.function.findData(step.get("function")), 0))
            self.text.blockSignals(True)
            self.text.setPlainText(in_language(self.stored["text"]))
            self.text.blockSignals(False)
            self.expected.setCurrentIndex(max(self.expected.findData(step.get("expected")), 0))
            self._show_instruction()
        self.step = step

    def _show_instruction(self) -> None:
        known = self.function.currentData() in self.instructions
        self.instruction_state.setText(
            tr("Connection diagram and instructions come from the collection.") if known
            else tr("There are no instructions for this measurement yet.")
        )
        placeholder = self.instructions.get(self.function.currentData())
        self.title.setPlaceholderText(placeholder.title if placeholder else "")

    def _store(self) -> None:
        if self.step is None:
            return
        kind = self.step.get("kind", "measure")
        self.step["title"] = kept(self.stored["title"], self.title.text().strip())
        if kind == "measure":
            self.step["function"] = self.function.currentData()
            if not self.step["title"]:
                del self.step["title"]
            self._show_instruction()
        else:
            self.step["text"] = kept(self.stored["text"], self.text.toPlainText().strip())
        if kind == "check":
            self.step["expected"] = self.expected.currentData()
        self.changed.emit()
