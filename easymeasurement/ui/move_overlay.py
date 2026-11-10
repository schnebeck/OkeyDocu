# EasyMeasurement - easymeasurement/ui/move_overlay.py
# Choosing the element measurements are booked onto, without dragging them there.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem

from .common import ROW_ID, AppContext
from .kind_catalog import KindCatalog
from .overlay import Overlay


class MoveOverlay(Overlay):
    """The structure of the installation, searchable; a double click books at once."""

    def __init__(self, app: AppContext, root_id: int, count: int, current: int | None,
                 parent=None):
        super().__init__("Verschieben nach", parent, width=520)
        self.ok_button.setText("Verschieben")
        self.search = QLineEdit(placeholderText="Element suchen …")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumHeight(320)
        self.items: dict[int, QTreeWidgetItem] = {}
        catalog = KindCatalog(app.db)
        below: dict[int | None, list] = {}
        root = app.db.asset(root_id)
        for row in app.db.assets(root["customer_id"]):
            below.setdefault(row["parent_id"], []).append(row)

        def add(parent, row) -> None:
            item = QTreeWidgetItem([row["name"]])
            item.setIcon(0, catalog.icon(row["kind"]))
            item.setToolTip(0, f"{catalog.label(row['kind'])}\nDoppelklick: hierhin verschieben")
            item.setData(0, ROW_ID, row["id"])
            self.items[row["id"]] = item
            parent.addChild(item) if parent else self.tree.addTopLevelItem(item)
            for child in below.get(row["id"], ()):
                add(item, child)

        add(None, root)
        self.tree.expandAll()
        self.tree.currentItemChanged.connect(lambda *_: self._update())
        self.tree.itemDoubleClicked.connect(lambda *_: self.accept())
        if current in self.items:
            self.tree.setCurrentItem(self.items[current])
        what = "Die gewählte Messung" if count == 1 else f"Die {count} gewählten Messungen"
        self.body.addWidget(QLabel(f"{what} auf dieses Element buchen:"))
        self.body.addWidget(self.search)
        self.body.addWidget(self.tree)
        self._update()

    def first_field(self):
        return self.search

    def chosen(self) -> int | None:
        item = self.tree.currentItem()
        return item.data(0, ROW_ID) if item is not None else None

    def _update(self) -> None:
        self.ok_button.setEnabled(self.chosen() is not None)

    def _filter(self, text: str) -> None:
        words = text.casefold().split()

        def show(item) -> bool:
            below = [show(item.child(i)) for i in range(item.childCount())]
            hit = all(word in item.text(0).casefold() for word in words)
            item.setHidden(not (hit or any(below)))
            return hit or any(below)

        for row in range(self.tree.topLevelItemCount()):
            show(self.tree.topLevelItem(row))
