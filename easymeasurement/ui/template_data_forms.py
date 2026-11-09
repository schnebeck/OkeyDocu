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

from ..model import FUNCTION_LABELS


class TemplateDataForms:
    """Field tables, and how measurements appear for 0, 1 and many of them."""

    def _form_fields(self, block: dict, form: QFormLayout) -> None:
        rows = block.setdefault("rows", [])
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Bezeichnung", "Inhalt"])
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
            rows.append(["Bezeichnung", ""])
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
                rows.append(["Bezeichnung", code])
                self._show_form()
                self._touched()
            else:
                table.setItem(row, 1, QTableWidgetItem((rows[row][1] + " " + code).strip()))

        add = QPushButton("Zeile hinzufügen")
        remove = QPushButton("Zeile entfernen")
        add.clicked.connect(add_row)
        remove.clicked.connect(remove_row)
        line = QHBoxLayout()
        line.addWidget(add)
        line.addWidget(remove)
        line.addWidget(self._placeholder_box(insert), 1)
        self.rows_table = table
        form.addRow(table)
        form.addRow(line)
        features = QCheckBox("Merkmale der geprüften Anlage anhängen (nur die ausgefüllten)")
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
        function.addItem("Alle Messfunktionen", "*")
        for key, label in FUNCTION_LABELS.items():
            function.addItem(label, key)
        function.setCurrentIndex(max(function.findData(block.get("function", "*")), 0))

        def function_changed() -> None:
            if function.currentData() == "*":
                block.pop("function", None)
            else:
                block["function"] = function.currentData()
            self._changed()

        function.currentIndexChanged.connect(function_changed)
        form.addRow("Zeigt", function)

        none = block.setdefault("none", {})
        show_text = QRadioButton("Satz anzeigen")
        hide = QRadioButton("Block ausblenden")
        (hide if none.get("hide") else show_text).setChecked(True)
        text = QLineEdit(str(none.get("text", "Nicht gemessen.")))
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
        form.addRow(QLabel("<b>Bei 0 Messungen</b>"))
        form.addRow(choice)
        form.addRow("Text", text)
        form.addRow("", self._placeholder_box(text.insert))

        one = block.setdefault("one", {})
        location = QCheckBox("Messort anzeigen")
        location.setChecked(one.get("location", True))

        def location_changed(checked: bool) -> None:
            one.pop("location", None)
            if not checked:
                one["location"] = False
            self._changed()

        location.toggled.connect(location_changed)
        form.addRow(QLabel("<b>Bei 1 Messung</b> (Formular)"))
        form.addRow(location)

        many = block.setdefault("many", {})
        summary = QCheckBox("Min- und Max-Zeile anzeigen")
        summary.setChecked(many.get("summary", True))
        summary.toggled.connect(lambda v: (many.__setitem__("summary", v), self._changed()))
        self.many_summary = summary
        form.addRow(QLabel("<b>Bei mehreren Messungen</b> (Tabelle)"))
        form.addRow(summary)
