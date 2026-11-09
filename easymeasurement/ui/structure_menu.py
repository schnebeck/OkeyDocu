# EasyMeasurement - easymeasurement/ui/structure_menu.py
# What can be done with elements of the structure: from the context menu and the keyboard.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QMenu, QMessageBox

from .common import ROW_ID
from .kind_catalog import KindCatalog
from .structure_cleanup import CleanupOverlay
from .structure_tree import UNPLACED, StructureTree


def kind_menu(menu: QMenu, catalog: KindCatalog, slot) -> None:
    """The kinds used most first, the rest one level down."""
    shown = catalog.most_used()
    for kind in shown:
        menu.addAction(catalog.icon(kind.key), kind.label, lambda k=kind.key: slot(k))
    rest = [kind for kind in catalog.all if kind not in shown]
    if rest:
        more = menu.addMenu("Weitere")
        for kind in sorted(rest, key=lambda k: k.label.casefold()):
            more.addAction(catalog.icon(kind.key), kind.label, lambda k=kind.key: slot(k))


class StructureActions(QObject):
    """Works on what is selected in the tree; the tree rebuilds after every change."""

    properties_requested = Signal(int)

    def __init__(self, tree: StructureTree):
        super().__init__(tree)
        self.tree = tree
        self.app = tree.app
        tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_menu)
        for keys, slot in ((QKeySequence.StandardKey.Delete, self.delete),
                           (QKeySequence("Ins"), self._new_at_cursor)):
            shortcut = QShortcut(keys, tree)
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            shortcut.activated.connect(slot)

    def _target(self) -> int | None:
        current = self.tree.current_id()
        return self.tree.root_id if current in (None, UNPLACED) else current

    def menu(self) -> QMenu:
        catalog = KindCatalog(self.app.db)
        menu = QMenu(self.tree)
        selected = self.tree.selected_ids()
        single = len(selected) <= 1 and self.tree.current_id() != UNPLACED
        kind_menu(menu.addMenu(QIcon.fromTheme("list-add"), "Neues Element darunter"), catalog,
                  self.new_element)
        if single and self.tree.current_id() is not None:
            menu.addAction(QIcon.fromTheme("edit-rename"), "Umbenennen",
                           self.rename).setShortcut(QKeySequence("F2"))
            kind_menu(menu.addMenu("Typ ändern"), catalog, self.change_kind)
            menu.addAction(QIcon.fromTheme("document-properties"), "Eigenschaften …",
                           lambda: self.properties_requested.emit(self._target()))
        if len(selected) > 1 or (selected and selected[0] != self.tree.root_id):
            kind_menu(menu.addMenu("Zusammenfassen unter neuem Element"), catalog, self.group)
        menu.addSeparator()
        menu.addAction(QIcon.fromTheme("edit-clear-all"), "Leere Elemente entfernen …",
                       self.clean_up)
        removable = [i for i in selected if i != self.tree.root_id]
        if removable:
            menu.addAction(QIcon.fromTheme("edit-delete"), "Löschen …",
                           self.delete).setShortcut(QKeySequence.StandardKey.Delete)
        return menu

    def _show_menu(self, position) -> None:
        if self.tree.root_id is not None or self.tree.customer_id is not None:
            self.menu().exec(self.tree.viewport().mapToGlobal(position))

    def _new_at_cursor(self) -> None:
        catalog = KindCatalog(self.app.db)
        menu = QMenu(self.tree)
        kind_menu(menu, catalog, self.new_element)
        current = self.tree.currentItem()
        spot = (self.tree.visualItemRect(current).bottomLeft() if current is not None
                else self.tree.rect().topLeft())
        menu.exec(self.tree.viewport().mapToGlobal(spot))

    # Changes -------------------------------------------------------------

    def new_element(self, kind: str) -> None:
        """Named after its kind and opened for typing the real name at once."""
        label = KindCatalog(self.app.db).label(kind)
        parent = self._target()
        if parent is None:
            created = self.app.db.add_asset(self.tree.customer_id, kind, label)
        else:
            created = self.app.service.add_element(parent, kind, label)
        self._rebuilt_with(created, edit=True)

    def group(self, kind: str) -> None:
        label = KindCatalog(self.app.db).label(kind)
        chosen = [i for i in self.tree.selected_ids() if i != self.tree.root_id]
        if chosen:
            self._rebuilt_with(self.app.service.group_elements(chosen, kind, label), edit=True)

    def change_kind(self, kind: str) -> None:
        for asset_id in self.tree.selected_ids() or [self._target()]:
            self.app.db.set_asset_kind(asset_id, kind)
        self._rebuilt_with(self._target())

    def rename(self) -> None:
        item = self.tree.currentItem()
        if item is not None and item.data(0, ROW_ID) != UNPLACED:
            self.tree.editItem(item, 0)

    def _rebuilt_with(self, asset_id: int, edit: bool = False) -> None:
        self.tree.reload()
        self.tree.select(asset_id)
        self.tree.changed.emit()
        if edit and asset_id in self.tree.items:
            self.tree.editItem(self.tree.items[asset_id], 0)

    def delete(self) -> None:
        chosen = [i for i in self.tree.selected_ids() if i != self.tree.root_id]
        if not chosen:
            return
        for asset_id in chosen:
            blocker = self.app.service.deletion_blocker(asset_id)
            if blocker:
                name = self.app.db.asset(asset_id)["name"]
                QMessageBox.information(self.tree, "Löschen", f"„{name}“ bleibt: {blocker}")
                return
        if not self._confirm(chosen):
            return
        parent = self.app.db.asset(chosen[0])["parent_id"]
        self.tree._apply(lambda: [self.app.service.delete_element(i) for i in chosen
                                  if self.app.db.asset(i) is not None])
        self.tree.select(parent)

    def _confirm(self, chosen: list[int]) -> bool:
        below = sum(len(self.app.service.subtree(i)) - 1 for i in chosen)
        names = ", ".join(f"„{self.app.db.asset(i)['name']}“" for i in chosen[:3])
        if len(chosen) > 3:
            names += f" und {len(chosen) - 3} weitere"
        text = f"{names} löschen?"
        detail = f"Mit {below} Elementen darunter. " if below else ""
        detail += "Messungen offener Kampagnen wandern eine Ebene nach oben."
        box = QMessageBox(QMessageBox.Icon.Question, "Löschen", text, parent=self.tree)
        box.setInformativeText(detail)
        delete = box.addButton("Löschen", QMessageBox.ButtonRole.DestructiveRole)
        box.setDefaultButton(box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole))
        box.exec()
        return box.clickedButton() is delete

    def clean_up(self) -> None:
        root = self._target()
        empty = self.app.service.empty_elements(root, self.tree.customer_id)
        overlay = CleanupOverlay(self.app, root, empty, self.tree.window())
        if overlay.exec():
            chosen = overlay.chosen()
            self.tree._apply(lambda: [self.app.service.delete_element(i) for i in chosen])
