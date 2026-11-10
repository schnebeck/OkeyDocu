# EasyMeasurement - easymeasurement/ui/master_data.py
# Customers on the left, the structure of the chosen one in the middle, the chosen thing on the right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import sqlite3

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..l10n import N_, tr
from .board import Board, GutterSplitter
from .campaign_list import heading
from .common import ROW_ID, AppContext, show_error
from .element_form import ElementForm
from .kind_catalog import CUSTOMER_ICON, element_icon
from .master_data_forms import CustomerForm
from .structure_panel import StructurePanel

ARRANGE_HINT = N_("Dragging reorders, even to the very top. Marking several and “Combine” puts"
                  " them under a new element, such as machines under an installation.")


class MasterDataPage(QWidget):
    """Like a file manager: customers are the drives, elements the folders."""

    changed = Signal()
    kinds_requested = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.customers = QListWidget()
        self.customers.currentItemChanged.connect(lambda item, _: self._customer_chosen(item))
        add_customer = QPushButton(tr("New customer"))
        add_customer.clicked.connect(self._add_customer)
        self.delete_button = QPushButton(tr("Delete …"))
        self.delete_button.clicked.connect(self._delete)
        buttons = QHBoxLayout()
        buttons.addWidget(add_customer)
        buttons.addWidget(self.delete_button)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(heading(tr("Customers"), 11))
        left_layout.addWidget(self.customers, 1)
        left_layout.addLayout(buttons)

        self.structure = StructurePanel(app)
        self.structure.set_hint(tr(ARRANGE_HINT))
        kinds = QToolButton(text=tr("Kinds …"))
        kinds.setToolTip(tr("Edit structure kinds and their features"))
        kinds.clicked.connect(self.kinds_requested)
        self.structure.bar.row.addWidget(kinds)
        self.structure.bar.even_out()
        self.tree = self.structure.tree
        self.tree.chosen.connect(self._element_chosen)
        self.tree.changed.connect(self.changed)
        self.structure.actions.properties_requested.connect(self.tree.select)

        self.customer_form = CustomerForm(app)
        self.customer_form.changed.connect(self._customer_changed)
        self.element_form = ElementForm(app)
        self.element_form.changed.connect(self._element_changed)
        self.forms = QStackedWidget()
        self.forms.addWidget(QLabel(tr("Choose or create a customer on the left.")))
        self.forms.addWidget(self.customer_form)
        self.forms.addWidget(self.element_form)
        self.form_title = heading("", 11)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.form_title)
        right_layout.addWidget(self.forms, 1)

        splitter = GutterSplitter(objectName="master-data")
        for pane in (left, Board("master-data-structure", self.structure), right):
            splitter.addWidget(pane)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([220, 380, 380])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        self.refresh()

    def refresh(self) -> None:
        keep = self.customer_id()
        self.customers.blockSignals(True)
        self.customers.clear()
        for row in self.app.db.customers():
            text = row["name"] + (f"\n{row['city']}" if row["city"] else "")
            item = QListWidgetItem(element_icon(CUSTOMER_ICON), text)
            item.setData(ROW_ID, row["id"])
            self.customers.addItem(item)
        self.customers.blockSignals(False)
        self.select_customer(keep if keep is not None else self._first_customer())

    def _first_customer(self) -> int | None:
        item = self.customers.item(0)
        return item.data(ROW_ID) if item else None

    def customer_id(self) -> int | None:
        item = self.customers.currentItem()
        return item.data(ROW_ID) if item else None

    def select_customer(self, customer_id: int | None) -> None:
        for row in range(self.customers.count()):
            if self.customers.item(row).data(ROW_ID) == customer_id:
                self.customers.setCurrentRow(row)
                return
        self._customer_chosen(None)

    def select_element(self, asset_id: int) -> None:
        self.select_customer(self.app.db.asset(asset_id)["customer_id"])
        self.tree.select(asset_id)

    def _customer_chosen(self, item) -> None:
        customer = item.data(ROW_ID) if item is not None else None
        self.delete_button.setEnabled(customer is not None)
        self.structure.setEnabled(customer is not None)
        self.tree.show_customer(customer)
        self.tree.setCurrentItem(None)
        self._element_chosen(None)

    def _element_chosen(self, asset_id) -> None:
        if asset_id is not None and self.app.db.asset(asset_id) is not None:
            self.element_form.load(asset_id)
            self.forms.setCurrentWidget(self.element_form)
            self.form_title.setText(tr("Element"))
        elif self.customer_id() is not None:
            self.customer_form.load(self.customer_id())
            self.forms.setCurrentWidget(self.customer_form)
            self.form_title.setText(tr("Customer"))
        else:
            self.forms.setCurrentIndex(0)
            self.form_title.setText("")

    def _customer_changed(self) -> None:
        item = self.customers.currentItem()
        row = self.app.db.customer(self.customer_id())
        item.setText(row["name"] + (f"\n{row['city']}" if row["city"] else ""))
        self.changed.emit()

    def _element_changed(self) -> None:
        self.tree.update_item(self.element_form.asset_id)
        self.changed.emit()

    def _add_customer(self) -> None:
        customer = self.app.db.add_customer(tr("New customer"))
        self.refresh()
        self.select_customer(customer)
        self.customer_form.fields["name"].setFocus()
        self.customer_form.fields["name"].selectAll()
        self.changed.emit()

    def _delete(self) -> None:
        """A customer goes only without installations; elements are deleted in the tree."""
        customer = self.customer_id()
        if customer is None:
            return
        name = self.app.db.customer(customer)["name"]
        answer = QMessageBox.question(self, tr("Delete"),
                                      tr("Delete the customer “{name}”?", name=name))
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.app.db.execute("DELETE FROM customers WHERE id=?", customer)
        except sqlite3.IntegrityError:
            show_error(self, tr("Not possible: the customer still has installations. Delete them"
                                  " first."))
            return
        self.refresh()
        self.changed.emit()
