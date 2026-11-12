# EasyMeasurement - easymeasurement/ui/structure_panel.py
# The structure beside the measurement table: search, new elements and the tree.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLineEdit, QVBoxLayout, QWidget

from ..l10n import N_, tr
from .board import Strip, menu_button
from .common import AppContext
from .kind_catalog import KindCatalog
from .structure_menu import StructureActions, kind_menu
from .structure_tree import StructureTree

DROP_HINT = N_("Drag measurements from the table onto an element to book them there."
               " New measurements go to the chosen element.")


class StructurePanel(QWidget):
    """Search and new elements in the bar, then the tree; its heading tells how to use it."""

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.tree = StructureTree(app)
        self.actions = StructureActions(self.tree)
        self.new_button = menu_button(tr("+ Element"),
                                      tr("Create an element below the chosen one (Ins)"))
        self.new_button.menu().aboutToShow.connect(self._fill_new_menu)
        self.search = QLineEdit(placeholderText=tr("Search elements …"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.filter)
        self.tree.changed.connect(lambda: self.filter(self.search.text()))
        self.set_hint(tr(DROP_HINT))
        self.bar = Strip()
        self.bar.row.addWidget(self.search, 1)
        self.bar.row.addWidget(self.new_button)
        self.bar.even_out()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.bar)
        layout.addWidget(self.tree, 1)
        self.tree.setFrameShape(QFrame.Shape.NoFrame)

    def set_hint(self, text: str) -> None:
        self.tree.headerItem().setToolTip(0, text)

    def filter(self, text: str) -> None:
        """Hits stay with the way to them; every word has to appear in the name."""
        words = text.casefold().split()

        def show(item) -> bool:
            below = [show(item.child(i)) for i in range(item.childCount())]
            hit = all(word in item.text(0).casefold() for word in words)
            item.setHidden(not (hit or any(below)))
            if words and any(below):
                item.setExpanded(True)
            return hit or any(below)

        for row in range(self.tree.topLevelItemCount()):
            show(self.tree.topLevelItem(row))

    def _fill_new_menu(self) -> None:
        menu = self.new_button.menu()
        menu.clear()
        kind_menu(menu, KindCatalog(self.app.db), self.actions.new_element)

