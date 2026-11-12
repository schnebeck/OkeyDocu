# EasyMeasurement - easymeasurement/ui/choice_table.py
# The values of a choice list as a table: one row per value, one column per attribute.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Each value row keeps what is not a cell, its help, curve, picture and methods, with its
first item. A cell shows a stored text in the current language and gives back the stored text
as long as it is not changed, so a shipped English text stays English underneath."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..l10n import in_language, tr
from ..store.choice_lists import ChoiceValue

STORED = Qt.ItemDataRole.UserRole  # the text as stored
ENTRY = Qt.ItemDataRole.UserRole + 1  # the ChoiceValue of the row, in its first item


def stored_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(in_language(text))
    item.setData(STORED, text)
    return item


def stored_text(item: QTableWidgetItem | None) -> str:
    if item is None:
        return ""
    text, kept = item.text().strip(), item.data(STORED) or ""
    return kept if text == in_language(kept) else text


class ChoiceTable(QWidget):
    edited = Signal()
    row_chosen = Signal(int)

    def __init__(self):
        super().__init__()
        self.table = QTableWidget(0, 1)
        self.table.verticalHeader().hide()
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(lambda _: self._changed())
        self.table.currentCellChanged.connect(lambda row, *_: self.row_chosen.emit(row))
        self.attribute = QLineEdit(placeholderText=tr("Name of a new property"))
        self.attribute.returnPressed.connect(self.add_attribute)
        values = QHBoxLayout()
        for text, slot in ((tr("Add value"), self.add_value), (tr("Remove value"), self.remove_value)):
            values.addWidget(self._button(text, slot))
        values.addStretch(1)
        for text, step, tip in (("▲", -1, tr("Move up")), ("▼", 1, tr("Move down"))):
            button = self._button(text, lambda _=False, step=step: self._move(step))
            button.setToolTip(tip)
            button.setFixedWidth(button.fontMetrics().horizontalAdvance("▲") + 24)
            values.addWidget(button)
        attributes = QHBoxLayout()
        attributes.addWidget(self.attribute, 1)
        attributes.addWidget(self._button(tr("Add property"), self.add_attribute))
        attributes.addWidget(self._button(tr("Remove property"), self.remove_attribute))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, 1)
        layout.addLayout(values)
        layout.addLayout(attributes)
        self._filling = False

    @staticmethod
    def _button(text: str, slot) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(slot)
        return button

    def show_values(self, attributes: tuple[str, ...], values: tuple[ChoiceValue, ...]) -> None:
        self._filling = True
        self.table.clear()
        self.table.setColumnCount(1 + len(attributes))
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderItem(0, QTableWidgetItem(tr("Value")))
        for column, name in enumerate(attributes, 1):
            self.table.setHorizontalHeaderItem(column, stored_item(name))
        for entry in values:
            self._append(entry)
        self.table.resizeColumnsToContents()
        self._filling = False

    def _append(self, entry: ChoiceValue) -> int:
        row = self.table.rowCount()
        self.table.insertRow(row)
        first = stored_item(entry.value)
        first.setData(ENTRY, entry)
        self.table.setItem(row, 0, first)
        for column, name in enumerate(self.attributes(), 1):
            self.table.setItem(row, column, stored_item(entry.facts.get(name, "")))
        return row

    def attributes(self) -> tuple[str, ...]:
        return tuple(stored_text(self.table.horizontalHeaderItem(column))
                     for column in range(1, self.table.columnCount()))

    def entry(self, row: int) -> ChoiceValue | None:
        item = self.table.item(row, 0)
        return item.data(ENTRY) if item is not None else None

    def set_entry(self, row: int, entry: ChoiceValue) -> None:
        """The parts of a value that are not cells, as the form below the table edits them."""
        item = self.table.item(row, 0)
        if item is not None:
            item.setData(ENTRY, entry)
            self._changed()

    def values(self) -> tuple[ChoiceValue, ...]:
        found, seen = [], set()
        names = self.attributes()
        for row in range(self.table.rowCount()):
            value = stored_text(self.table.item(row, 0))
            if not value or value in seen:
                continue
            seen.add(value)
            facts = {name: stored_text(self.table.item(row, column))
                     for column, name in enumerate(names, 1)}
            kept = self.entry(row) or ChoiceValue(value)
            found.append(replace(kept, value=value,
                                 facts={name: text for name, text in facts.items() if text}))
        return tuple(found)

    def add_value(self) -> None:
        self._filling = True
        row = self._append(ChoiceValue(""))
        self._filling = False
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))

    def remove_value(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._changed()

    def add_attribute(self) -> None:
        name = self.attribute.text().strip()
        if not name or name in self.attributes():
            return
        self._filling = True
        column = self.table.columnCount()
        self.table.insertColumn(column)
        self.table.setHorizontalHeaderItem(column, stored_item(name))
        for row in range(self.table.rowCount()):
            self.table.setItem(row, column, stored_item(""))
        self._filling = False
        self.attribute.clear()
        self._changed()

    def remove_attribute(self) -> None:
        column = self.table.currentColumn()
        if column > 0:
            self.table.removeColumn(column)
            self._changed()

    def _move(self, step: int) -> None:
        row = self.table.currentRow()
        target = row + step
        if row < 0 or not 0 <= target < self.table.rowCount():
            return
        self._filling = True
        for column in range(self.table.columnCount()):
            upper, lower = self.table.takeItem(row, column), self.table.takeItem(target, column)
            self.table.setItem(row, column, lower)
            self.table.setItem(target, column, upper)
        self._filling = False
        self.table.setCurrentCell(target, self.table.currentColumn())
        self._changed()

    def _changed(self) -> None:
        if not self._filling:
            self.edited.emit()
