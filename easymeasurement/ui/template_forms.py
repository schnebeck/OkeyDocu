# EasyMeasurement - easymeasurement/ui/template_forms.py
# The property forms of the template editor: choosing the form, and those for plain text.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from ..reporting.template_model import BLOCK_LABELS, CONDITIONS, PLACEHOLDERS


class TemplateForms:
    """Each block type finds its form by name, as `_form_` and the type."""

    # Property forms ------------------------------------------------------

    def _show_form(self) -> None:
        self._update_buttons()
        path = self.path()
        page = QWidget()
        form = QFormLayout(page)
        self.form = form
        if path is None:
            form.addRow(QLabel("Oben einen Block wählen oder hinzufügen."))
        else:
            block = self._block(path)
            title = QLabel(f"<b>{BLOCK_LABELS.get(block['type'], block['type'])}</b>")
            form.addRow(title)
            builder = getattr(self, f"_form_{block['type']}", None)
            if builder:
                builder(block, form)
            if block["type"] != "steps":
                self._condition_row(block, form)
        self.form_host.setWidget(page)

    def _changed(self) -> None:
        self._refresh_label()
        self._touched()

    def _placeholder_box(self, insert) -> QComboBox:
        box = QComboBox()
        box.addItem("Datenfeld einfügen …", None)
        for label, code in PLACEHOLDERS:
            box.addItem(label, code)

        def chosen(index: int) -> None:
            code = box.itemData(index)
            if code:
                insert(code)
                box.setCurrentIndex(0)

        box.activated.connect(chosen)
        return box

    def _text_rows(self, block: dict, form: QFormLayout, multi_line: bool) -> None:
        if multi_line:
            field = QPlainTextEdit(str(block.get("text", "")))
            field.setMaximumHeight(110)
            field.textChanged.connect(
                lambda: (block.__setitem__("text", field.toPlainText()), self._changed())
            )
            insert = field.insertPlainText
        else:
            field = QLineEdit(str(block.get("text", "")))
            field.textChanged.connect(
                lambda text: (block.__setitem__("text", text), self._changed())
            )
            insert = field.insert
        self.text_field = field
        form.addRow("Text", field)
        form.addRow("", self._placeholder_box(insert))

    def _form_heading(self, block: dict, form: QFormLayout) -> None:
        self._text_rows(block, form, multi_line=False)
        level = QSpinBox(minimum=1, maximum=3, value=int(block.get("level", 1)))
        level.valueChanged.connect(lambda v: (block.__setitem__("level", v), self._changed()))
        form.addRow("Ebene", level)

    def _form_text(self, block: dict, form: QFormLayout) -> None:
        self._text_rows(block, form, multi_line=True)

    _form_notice = _form_text

    def _form_steps(self, block: dict, form: QFormLayout) -> None:
        form.addRow(QLabel(
            "Alles, was hier eingerückt steht, erscheint im Protokoll einmal je Messschritt\n"
            "oder, ohne Messplan, einmal je Messgröße."
        ))

    def _form_attachments(self, block: dict, form: QFormLayout) -> None:
        form.addRow(QLabel(
            "Notizen und Dateien an Orten der Anlage oder an der Kampagne selbst.\n"
            "Was an einer Messung hängt, steht im Protokoll bei dieser Messung."
        ))

    def _form_signature(self, block: dict, form: QFormLayout) -> None:
        field = QLineEdit(", ".join(block.get("labels", [])))

        def changed(text: str) -> None:
            block["labels"] = [part.strip() for part in text.split(",") if part.strip()] or [""]
            self._changed()

        field.textChanged.connect(changed)
        form.addRow("Felder (mit Komma getrennt)", field)

    def _condition_row(self, block: dict, form: QFormLayout) -> None:
        box = QComboBox()
        for label, value in CONDITIONS:
            box.addItem(label, value)
        current = block.get("when")
        index = box.findData(current)
        if current is not None and index < 0:  # written by hand in the source view
            box.addItem(f"Eigene Bedingung: {current}", current)
            index = box.count() - 1
        box.setCurrentIndex(max(index, 0))

        def changed() -> None:
            block.pop("when", None)
            if box.currentData() is not None:
                block["when"] = box.currentData()
            self._changed()

        box.currentIndexChanged.connect(changed)
        self.condition = box
        form.addRow("Anzeige", box)
