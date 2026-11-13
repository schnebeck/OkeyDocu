# OkeyDocu - okeydocu/ui/choice_lists_page.py
# Settings for the choice lists: their values with facts, help, curve, picture and methods.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..l10n import in_language, tr
from ..store.choice_lists import ChoiceList
from ..store.kinds import slug
from .board import GutterSplitter
from .campaign_items import heading
from .choice_table import ChoiceTable
from .choice_value_form import ValueForm
from .common import ROW_ID, AppContext


class ChoiceListsPage(QWidget):
    """Every change is stored at once and offered by every feature using the list."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.lists = QListWidget()
        self.lists.currentItemChanged.connect(lambda item, _: self._show(item))
        add = QPushButton(tr("New list"))
        add.clicked.connect(self._add)
        self.remove_button = QPushButton(tr("Delete"))
        self.remove_button.clicked.connect(self._remove)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(self.remove_button)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(heading(tr("Choice lists"), 11))
        left_layout.addWidget(self.lists, 1)
        left_layout.addLayout(buttons)

        self.label = QLineEdit()
        self.label.editingFinished.connect(self._save)
        self.help = QPlainTextEdit()
        self.help.setPlaceholderText(tr("What the list is about, told while no value is chosen"))
        self.help.setFixedHeight(4 * self.fontMetrics().height())
        self.help.textChanged.connect(self._save)
        self.table = ChoiceTable()
        self.table.edited.connect(self._save)
        self.table.row_chosen.connect(self._row_chosen)
        self.value_form = ValueForm()
        self.value_form.edited.connect(self._value_edited)
        form = QFormLayout()
        form.addRow(tr("Label"), self.label)
        form.addRow(tr("Help"), self.help)
        self.editor = QWidget()
        right = QVBoxLayout(self.editor)
        right.setContentsMargins(0, 0, 0, 0)
        right.addLayout(form)
        right.addWidget(heading(tr("Values"), 11))
        right.addWidget(self.table, 1)
        right.addWidget(heading(tr("Chosen value"), 11))
        right.addWidget(self.value_form)

        splitter = GutterSplitter(objectName="choice_lists")
        splitter.addWidget(left)
        splitter.addWidget(self.editor)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([260, 800])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        self.shown: ChoiceList | None = None
        self._filling = False
        self.refresh()

    def refresh(self, select: str | None = None) -> None:
        keep = select or self.current_key()
        self.lists.blockSignals(True)
        self.lists.clear()
        for chosen in sorted(self.app.db.choice_lists().values(),
                             key=lambda found: in_language(found.label).casefold()):
            used = self.app.db.choice_list_usage(chosen.key)
            usage = tr("{count} features", count=used) if used else tr("unused")
            item = QListWidgetItem(f"{in_language(chosen.label)}\n{usage}")
            item.setData(ROW_ID, chosen.key)
            self.lists.addItem(item)
            if chosen.key == keep:
                self.lists.setCurrentItem(item)
        self.lists.blockSignals(False)
        if self.lists.currentItem() is None and self.lists.count():
            self.lists.setCurrentRow(0)
        self._show(self.lists.currentItem())

    def current_key(self) -> str | None:
        item = self.lists.currentItem()
        return item.data(ROW_ID) if item is not None else None

    def _show(self, item) -> None:
        chosen = self.app.db.choice_list(item.data(ROW_ID)) if item is not None else None
        self.shown = chosen
        self.editor.setEnabled(chosen is not None)
        self.remove_button.setEnabled(chosen is not None)
        if chosen is None:
            return
        self._filling = True
        self.label.setText(in_language(chosen.label))
        self.help.setPlainText(in_language(chosen.help))
        self.table.show_values(chosen.attributes, chosen.values)
        self.value_form.show_entry(None)
        self._filling = False

    def _row_chosen(self, row: int) -> None:
        self.value_form.show_entry(self.table.entry(row) if row >= 0 else None)

    def _value_edited(self, entry) -> None:
        self.table.set_entry(self.table.table.currentRow(), entry)

    def _kept(self, typed: str, stored: str) -> str:
        return stored if typed == in_language(stored) else typed

    def _save(self) -> None:
        if self._filling or self.shown is None:
            return
        label = self._kept(self.label.text().strip(), self.shown.label) or self.shown.label
        edited = ChoiceList(self.shown.key, label,
                            self._kept(self.help.toPlainText().strip(), self.shown.help),
                            self.table.attributes(), self.table.values())
        if edited != self.shown:
            self.app.db.save_choice_list(edited)
            self.shown = edited
            item = self.lists.currentItem()
            item.setText(in_language(label) + "\n" + item.text().split("\n", 1)[1])
            self.changed.emit()

    def _add(self) -> None:
        label = tr("New list")
        taken = set(self.app.db.choice_lists())
        key, number = slug(label), 2
        while key in taken:
            key, number = f"{slug(label)}_{number}", number + 1
        self.app.db.save_choice_list(ChoiceList(key, label))
        self.refresh(select=key)
        self.label.setFocus()
        self.label.selectAll()
        self.changed.emit()

    def _remove(self) -> None:
        key = self.current_key()
        if key is not None:
            self.app.db.delete_choice_list(key)
            self.refresh()
            self.changed.emit()
