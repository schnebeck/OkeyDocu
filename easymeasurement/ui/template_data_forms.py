# EasyMeasurement - easymeasurement/ui/template_data_forms.py
# The property forms of the template editor for blocks that show data.
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
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QTableWidget,
    QTableWidgetItem,
)

from ..l10n import tr
from ..vocabulary import function_keys, function_label


class TemplateDataForms:
    """Field tables, and how measurements appear for 0, 1 and many of them."""

    def _form_fields(self, block: dict, form: QFormLayout) -> None:
        rows = block.setdefault("rows", [])
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels([tr("Label"), tr("Content")])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().hide()
        table.setMinimumHeight(150)
        for index, (label, value) in enumerate(rows):
            table.setItem(index, 0, QTableWidgetItem(str(label)))
            table.setItem(index, 1, QTableWidgetItem(str(value)))

        def edited(item: QTableWidgetItem) -> None:
            rows[item.row()][item.column()] = item.text()
            self._changed()

        table.itemChanged.connect(edited)

        def add_row() -> None:
            rows.append([tr("Designation"), ""])
            self._show_form()
            self._touched()

        def remove_row() -> None:
            if table.currentRow() >= 0:
                rows.pop(table.currentRow())
                self._show_form()
                self._touched()

        def insert(code: str) -> None:
            row = table.currentRow()
            if row < 0:
                rows.append([tr("Designation"), code])
                self._show_form()
                self._touched()
            else:
                table.setItem(row, 1, QTableWidgetItem((rows[row][1] + " " + code).strip()))

        add = QPushButton(tr("Add row"))
        remove = QPushButton(tr("Remove row"))
        add.clicked.connect(add_row)
        remove.clicked.connect(remove_row)
        line = QHBoxLayout()
        line.addWidget(add)
        line.addWidget(remove)
        line.addWidget(self._placeholder_box(insert), 1)
        self.rows_table = table
        form.addRow(table)
        form.addRow(line)
        features = QCheckBox(
            tr("Append features of the inspected installation (only the filled-in ones)"))
        features.setChecked(block.get("features") == "asset")

        def toggled(on: bool) -> None:
            if on:
                block["features"] = "asset"
            else:
                block.pop("features", None)
            self._touched()

        features.toggled.connect(toggled)
        self.features_box = features
        form.addRow(features)

    def _form_measurements(self, block: dict, form: QFormLayout) -> None:
        function = QComboBox()
        function.addItem(tr("All measurements and checks"), "*")
        for key in function_keys():
            function.addItem(function_label(key), key)
        function.setCurrentIndex(max(function.findData(block.get("function", "*")), 0))

        def function_changed() -> None:
            if function.currentData() == "*":
                block.pop("function", None)
            else:
                block["function"] = function.currentData()
            self._changed()

        function.currentIndexChanged.connect(function_changed)
        form.addRow(tr("Shows"), function)

        none = block.setdefault("none", {})
        show_text = QRadioButton(tr("Show sentence"))
        hide = QRadioButton(tr("Hide block"))
        (hide if none.get("hide") else show_text).setChecked(True)
        text = QLineEdit(str(none.get("text", tr("Not measured."))))
        text.setEnabled(not none.get("hide"))

        def none_changed() -> None:
            text.setEnabled(show_text.isChecked())
            none.clear()
            if show_text.isChecked():
                none["text"] = text.text()
            else:
                none["hide"] = True
            self._changed()

        show_text.toggled.connect(none_changed)
        text.textChanged.connect(none_changed)
        choice = QHBoxLayout()
        choice.addWidget(show_text)
        choice.addWidget(hide)
        choice.addStretch()
        self.none_hide, self.none_text = hide, text
        form.addRow(QLabel(tr("<b>With 0 measurements</b>")))
        form.addRow(choice)
        form.addRow(tr("Text"), text)
        form.addRow("", self._placeholder_box(text.insert))

        one = block.setdefault("one", {})
        location = QCheckBox(tr("Show measuring location"))
        location.setChecked(one.get("location", True))

        def location_changed(checked: bool) -> None:
            one.pop("location", None)
            if not checked:
                one["location"] = False
            self._changed()

        location.toggled.connect(location_changed)
        form.addRow(QLabel(tr("<b>With 1 measurement</b> (form)")))
        form.addRow(location)

        many = block.setdefault("many", {})
        summary = QCheckBox(tr("Show min and max row"))
        summary.setChecked(many.get("summary", True))
        summary.toggled.connect(lambda v: (many.__setitem__("summary", v), self._changed()))
        self.many_summary = summary
        form.addRow(QLabel(tr("<b>With several measurements</b> (table)")))
        form.addRow(summary)
