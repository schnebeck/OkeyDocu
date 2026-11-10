# EasyMeasurement - easymeasurement/ui/structure_panel.py
# The structure beside the measurement table, and the chosen element in the side panel.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..l10n import N_, tr
from .place_files import PlaceFiles
from .board import Strip, menu_button
from .common import AppContext
from .dashboard_card import dim
from .element_form import TEXTS, interval_text
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


class PlacePanel(QWidget):
    """What is known about the chosen element; empty features are left out."""

    properties_requested = Signal(int)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.asset_id: int | None = None
        self.icon = QLabel()
        self.name = QLabel()
        self.name.setWordWrap(True)
        font = self.name.font()
        font.setBold(True)
        self.name.setFont(font)
        self.kind = dim(QLabel())
        self.details = QLabel()
        self.details.setWordWrap(True)
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.muted = self.kind.palette().color(self.kind.foregroundRole()).name()
        self.edit_button = QPushButton(tr("Properties …"))
        self.edit_button.clicked.connect(lambda: self.properties_requested.emit(self.asset_id))
        self.files = PlaceFiles(app, tr("this location"))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(self.name)
        names.addWidget(self.kind)
        names.addStretch(1)
        top = QHBoxLayout()
        top.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(names, 1)
        top.addWidget(self.edit_button, 0, Qt.AlignmentFlag.AlignTop)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self.details)
        layout.addWidget(self.files)
        layout.addStretch(1)

    def show_element(self, asset_id: int | None, campaign_id: int | None, editable: bool) -> None:
        self.asset_id = asset_id
        row = self.app.db.asset(asset_id) if asset_id is not None else None
        self.setVisible(row is not None)
        if row is None:
            self.files.show_target(None)
            return
        catalog = KindCatalog(self.app.db)
        kind = catalog.by_key.get(row["kind"])
        self.icon.setPixmap(catalog.icon(row["kind"]).pixmap(32, 32))
        self.name.setText(row["name"])
        self.kind.setText(catalog.label(row["kind"]))
        self.details.setText(self._details(row, kind))
        self.details.setVisible(bool(self.details.text()))
        self.files.target_name = row["name"]
        self.files.show_target(campaign_id, editable, asset_id=asset_id)

    def _details(self, row, kind) -> str:
        lines = [(tr(TEXTS[key]), row[key]) for key in ("identifier", "manufacturer", "type",
                                                     "serial_no", "comment") if row[key]]
        values = self.app.db.asset_features(row["id"])
        for feature in kind.features if kind else ():
            if values.get(feature.key):
                lines.append((feature.label, f"{values[feature.key]}\u202f{feature.unit}".strip()))
        months = row["interval_months"]
        if months is None and kind is not None:
            months = kind.interval_months
        if months:
            lines.append((tr("Inspection interval"), interval_text(months)))
        rows = "".join(f"<tr><td style='padding-right:10px; color:{self.muted}'>{escape(k)}</td>"
                       f"<td>{escape(v)}</td></tr>" for k, v in lines)
        return f"<table>{rows}</table>" if rows else ""
