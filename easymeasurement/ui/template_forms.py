# EasyMeasurement - easymeasurement/ui/template_forms.py
# The property forms of the template editor: choosing the form, and those for plain text.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QWidget,
)

from ..l10n import tr
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
            form.addRow(QLabel(tr("Choose or add a block above.")))
        else:
            block = self._block(path)
            label = BLOCK_LABELS.get(block["type"])
            title = QLabel(f"<b>{tr(label) if label else block['type']}</b>")
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
        box.addItem(tr("Insert data field …"), None)
        for label, code in PLACEHOLDERS:
            box.addItem(tr(label), code)

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
        form.addRow(tr("Text"), field)
        form.addRow("", self._placeholder_box(insert))

    def _form_heading(self, block: dict, form: QFormLayout) -> None:
        self._text_rows(block, form, multi_line=False)
        level = QSpinBox(minimum=1, maximum=3, value=int(block.get("level", 1)))
        level.valueChanged.connect(lambda v: (block.__setitem__("level", v), self._changed()))
        form.addRow(tr("Level"), level)

    def _form_text(self, block: dict, form: QFormLayout) -> None:
        self._text_rows(block, form, multi_line=True)

    _form_notice = _form_text

    def _form_steps(self, block: dict, form: QFormLayout) -> None:
        form.addRow(QLabel(tr(
            "Everything indented here appears in the report once per step\n"
            "or, without a test plan, once per measured quantity."
        )))

    def _form_attachments(self, block: dict, form: QFormLayout) -> None:
        form.addRow(QLabel(tr(
            "Notes and files at locations of the installation or at the campaign itself.\n"
            "What belongs to a measurement appears in the report with that measurement."
        )))

    def _form_letterhead(self, block: dict, form: QFormLayout) -> None:
        """One shared choice of data fields writes into the text field used last."""
        title = QLineEdit(str(block.get("title", "")))
        title.textChanged.connect(lambda text: (block.__setitem__("title", text), self._changed()))
        form.addRow(tr("Title"), title)
        edits = [self._lines_row(block, key, label, form) for key, label in (
            ("lines", tr("Lines below the title")), ("client", tr("Client")),
            ("contractor", tr("Contractor")))]
        edits[-1].setPlaceholderText(tr("One line per entry; the own company is under"
                                        " Settings → Company"))
        self.letterhead_target = edits[0]
        for edit in edits:  # a click into a field places its cursor
            edit.cursorPositionChanged.connect(
                lambda edit=edit: setattr(self, "letterhead_target", edit))
        form.addRow("", self._placeholder_box(
            lambda code: self.letterhead_target.insertPlainText(code)))
        code = QCheckBox(tr("QR code with the identifier of the inspection"))
        code.setChecked(bool(block.get("qr", True)))
        code.toggled.connect(lambda on: (block.__setitem__("qr", on), self._changed()))
        form.addRow("", code)
        logo = QCheckBox(tr("Company logo to the right of the title (Settings → Company)"))
        logo.setChecked(bool(block.get("logo", True)))
        logo.toggled.connect(lambda on: (block.__setitem__("logo", on), self._changed()))
        form.addRow("", logo)

    def _lines_row(self, block: dict, key: str, label: str, form: QFormLayout) -> QPlainTextEdit:
        edit = QPlainTextEdit("\n".join(block.get(key, [])))
        edit.setMaximumHeight(84)
        edit.textChanged.connect(lambda: (
            block.__setitem__(key, [line for line in edit.toPlainText().split("\n")]),
            self._changed()))
        form.addRow(label, edit)
        return edit

    def _form_signature(self, block: dict, form: QFormLayout) -> None:
        result = QLineEdit(str(block.get("result", "")))
        result.setPlaceholderText(tr("empty: without frame and result"))
        result.textChanged.connect(lambda text: (block.__setitem__("result", text),
                                                 self._changed()))
        form.addRow(tr("Result above"), result)
        form.addRow("", self._placeholder_box(result.insert))
        field = QLineEdit(", ".join(block.get("labels", [])))

        def changed(text: str) -> None:
            block["labels"] = [part.strip() for part in text.split(",") if part.strip()] or [""]
            self._changed()

        field.textChanged.connect(changed)
        form.addRow(tr("Fields (separated by commas)"), field)

    def _condition_row(self, block: dict, form: QFormLayout) -> None:
        box = QComboBox()
        for label, value in CONDITIONS:
            box.addItem(tr(label), value)
        current = block.get("when")
        index = box.findData(current)
        if current is not None and index < 0:  # written by hand in the source view
            box.addItem(tr("Custom condition: {condition}", condition=current), current)
            index = box.count() - 1
        box.setCurrentIndex(max(index, 0))

        def changed() -> None:
            block.pop("when", None)
            if box.currentData() is not None:
                block["when"] = box.currentData()
            self._changed()

        box.currentIndexChanged.connect(changed)
        self.condition = box
        form.addRow(tr("Display"), box)
