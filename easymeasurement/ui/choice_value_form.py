# EasyMeasurement - easymeasurement/ui/choice_value_form.py
# What a value of a choice list holds besides its cells: help, curve, picture and methods.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QWidget,
)

from ..l10n import in_language, tr
from ..store.choice_lists import ChoiceValue, Method
from ..vocabulary import function_keys, function_label
from .choice_table import stored_item, stored_text
from .curve_picture import parse_curve

PREVIEW_PX = 120
PICTURES = "*.png *.jpg *.jpeg *.svg"


class ValueForm(QWidget):
    """Every change is handed on at once through `edited` with the value as it now stands."""

    edited = Signal(object)

    def __init__(self):
        super().__init__()
        self.entry: ChoiceValue | None = None
        self.help = QPlainTextEdit()
        self.help.setPlaceholderText(tr("What to know about the value, a few paragraphs"))
        self.help.setFixedHeight(5 * self.fontMetrics().height())
        self.help.textChanged.connect(self._changed)
        self.curve = QLineEdit(placeholderText="breaker 3 5")
        self.curve.setToolTip(tr(
            "A circuit breaker: “breaker”, then the instantaneous trip range in multiples of the"
            " rated current, optionally the conventional non-tripping and tripping currents."))
        self.curve.editingFinished.connect(self._changed)
        self.preview = QLabel()
        load = QPushButton(tr("Picture …"))
        load.clicked.connect(self._load)
        drop = QPushButton(tr("Remove picture"))
        drop.clicked.connect(self._drop)
        picture = QHBoxLayout()
        picture.addWidget(self.preview)
        picture.addWidget(load)
        picture.addWidget(drop)
        picture.addStretch(1)
        self.methods = QTableWidget(0, 2)
        self.methods.setHorizontalHeaderLabels([tr("Measurement"), tr("What to mind")])
        self.methods.horizontalHeader().setStretchLastSection(True)
        self.methods.verticalHeader().hide()
        self.methods.setFixedHeight(5 * self.fontMetrics().height())
        self.methods.itemChanged.connect(lambda _: self._changed())
        add = QPushButton(tr("Add measurement"))
        add.clicked.connect(lambda: self._add_method(Method("")))
        remove = QPushButton(tr("Remove measurement"))
        remove.clicked.connect(self._remove_method)
        method_buttons = QHBoxLayout()
        method_buttons.addWidget(add)
        method_buttons.addWidget(remove)
        method_buttons.addStretch(1)
        form = QFormLayout(self)
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(tr("Help"), self.help)
        form.addRow(tr("Curve"), self.curve)
        form.addRow(tr("Picture"), picture)
        form.addRow(tr("Measurements"), self.methods)
        form.addRow("", method_buttons)
        self._filling = False
        self.show_entry(None)

    def show_entry(self, entry: ChoiceValue | None) -> None:
        self._filling = True
        self.entry = entry
        self.setEnabled(entry is not None)
        entry = entry or ChoiceValue("")
        self.help.setPlainText(in_language(entry.help))
        self.curve.setText(entry.curve)
        self._preview(entry.picture)
        self.methods.setRowCount(0)
        for method in entry.methods:
            self._add_method(method)
        self._filling = False

    def _add_method(self, method: Method) -> None:
        row = self.methods.rowCount()
        self.methods.insertRow(row)
        box = QComboBox()
        box.addItem("", "")
        for key in function_keys():
            box.addItem(function_label(key), key)
        box.setCurrentIndex(max(box.findData(method.function), 0))
        box.currentIndexChanged.connect(lambda _: self._changed())
        self.methods.setCellWidget(row, 0, box)
        self.methods.setItem(row, 1, stored_item(method.note))
        self.methods.resizeColumnToContents(0)
        self._changed()

    def _remove_method(self) -> None:
        row = self.methods.currentRow()
        if row >= 0:
            self.methods.removeRow(row)
            self._changed()

    def _load(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, tr("Picture"), "", PICTURES)
        if path and self.entry is not None:
            self.entry = replace(self.entry, picture=Path(path).read_bytes())
            self._preview(self.entry.picture)
            self._changed()

    def _drop(self) -> None:
        if self.entry is not None:
            self.entry = replace(self.entry, picture=b"")
            self._preview(b"")
            self._changed()

    def _preview(self, data: bytes) -> None:
        shown = QPixmap()
        if data and shown.loadFromData(data):
            self.preview.setPixmap(shown.scaled(PREVIEW_PX, PREVIEW_PX,
                                                Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
        else:
            self.preview.setText(tr("none", context="picture"))

    def current(self) -> ChoiceValue | None:
        if self.entry is None:
            return None
        methods, seen = [], set()
        for row in range(self.methods.rowCount()):
            function = self.methods.cellWidget(row, 0).currentData()
            if function and function not in seen:
                seen.add(function)
                methods.append(Method(function, stored_text(self.methods.item(row, 1))))
        typed = self.help.toPlainText().strip()
        help_text = self.entry.help if typed == in_language(self.entry.help) else typed
        curve = self.curve.text().strip()
        self.curve.setStyleSheet("" if not curve or parse_curve(curve) else "color: #c0392b;")
        return replace(self.entry, help=help_text, curve=curve, methods=tuple(methods))

    def _changed(self) -> None:
        if not self._filling and self.entry is not None:
            self.entry = self.current()
            self.edited.emit(self.entry)
