# OkeyDocu - okeydocu/ui/kind_features.py
# The features of one kind as an editable table: name, unit and list, in the order shown.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..l10n import in_language, tr
from ..store.choice_lists import ChoiceList
from ..store.kinds import Feature, slug

KEY = Qt.ItemDataRole.UserRole
COLUMNS = 3  # feature, unit, choice list


class ListDelegate(QStyledItemDelegate):
    """The list column is edited by choosing one of the lists, or none."""

    def __init__(self, table: "FeatureTable"):
        super().__init__(table)
        self.owner = table

    def createEditor(self, parent, option, index):  # noqa: N802 - Qt's name
        box = QComboBox(parent)
        box.addItem(tr("none", context="choice list"), None)
        for key, offered in self.owner.lists.items():
            box.addItem(in_language(offered.label), key)
        return box

    def setEditorData(self, editor, index):  # noqa: N802 - Qt's name
        editor.setCurrentIndex(max(editor.findData(index.data(KEY)), 0))

    def setModelData(self, editor, model, index):  # noqa: N802 - Qt's name
        model.setData(index, editor.currentData(), KEY)
        model.setData(index, editor.currentText() if editor.currentData() else "")


class FeatureTable(QWidget):
    """A renamed feature keeps its key, so values noted under the old name stay."""

    edited = Signal()

    def __init__(self):
        super().__init__()
        self.table = QTableWidget(0, COLUMNS)
        self.lists: dict[str, ChoiceList] = {}
        self.table.setHorizontalHeaderLabels([tr("Feature"), tr("Unit"), tr("Choice list")])
        self.table.horizontalHeaderItem(2).setToolTip(tr(
            "The list whose values the feature offers; any other may still be typed. The lists"
            " are edited under Settings → Choice lists."))
        self.table.setItemDelegateForColumn(2, ListDelegate(self))
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(self.table.fontMetrics().height() + 10)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.itemChanged.connect(lambda _: self._changed())
        self.add_button = QPushButton(tr("Add feature"))
        self.add_button.clicked.connect(self.add)
        self.remove_button = QPushButton(tr("Remove"))
        self.remove_button.clicked.connect(self.remove)
        self.up_button = QPushButton("▲")
        self.up_button.setToolTip(tr("Move up"))
        self.up_button.clicked.connect(lambda: self._move(-1))
        self.down_button = QPushButton("▼")
        self.down_button.setToolTip(tr("Move down"))
        self.down_button.clicked.connect(lambda: self._move(1))
        for button in (self.up_button, self.down_button):
            button.setFixedWidth(button.fontMetrics().horizontalAdvance("▲") + 24)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        buttons.addWidget(self.up_button)
        buttons.addWidget(self.down_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        self._filling = False

    def show_features(self, features: tuple[Feature, ...],
                      lists: dict[str, ChoiceList] | None = None) -> None:
        self.lists = lists or {}
        self._filling = True
        self.table.setRowCount(0)
        for feature in features:
            self._append(feature)
        self._filling = False

    def _append(self, feature: Feature) -> int:
        row = self.table.rowCount()
        self.table.insertRow(row)
        name = QTableWidgetItem(feature.label)
        name.setData(KEY, feature.key)
        self.table.setItem(row, 0, name)
        self.table.setItem(row, 1, QTableWidgetItem(feature.unit))
        offered = self.lists.get(feature.choice_list or "")
        chosen = QTableWidgetItem(in_language(offered.label) if offered else "")
        chosen.setData(KEY, feature.choice_list if offered else None)
        self.table.setItem(row, 2, chosen)
        return row

    def features(self) -> tuple[Feature, ...]:
        found, keys = [], set()
        for row in range(self.table.rowCount()):
            name, unit = self.table.item(row, 0), self.table.item(row, 1)
            offered = self.table.item(row, 2)
            label = name.text().strip() if name else ""
            if not label:
                continue
            key = name.data(KEY) or slug(label)
            while key in keys:
                key += "_"
            keys.add(key)
            if not name.data(KEY):  # from now on the feature keeps this key
                self._filling, was = True, self._filling
                name.setData(KEY, key)
                self._filling = was
            found.append(Feature(key, label, unit.text().strip() if unit else "",
                                 offered.data(KEY) if offered else None))
        return tuple(found)

    def add(self) -> None:
        self._filling = True
        row = self._append(Feature("", tr("New feature")))
        self._filling = False
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))
        self._changed()

    def remove(self) -> None:
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._changed()

    def _move(self, step: int) -> None:
        row = self.table.currentRow()
        target = row + step
        if row < 0 or not 0 <= target < self.table.rowCount():
            return
        self._filling = True
        for column in range(COLUMNS):
            upper, lower = self.table.takeItem(row, column), self.table.takeItem(target, column)
            self.table.setItem(row, column, lower)
            self.table.setItem(target, column, upper)
        self._filling = False
        self.table.setCurrentCell(target, 0)
        self._changed()

    def _changed(self) -> None:
        if not self._filling:
            self.edited.emit()
