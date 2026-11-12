# EasyMeasurement - easymeasurement/ui/structure_tree.py
# The structure of an installation like folders in a file manager, with the measurements on it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QPalette
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTreeWidget, QTreeWidgetItem

from ..campaign.service import StructureError
from ..store import CampaignClosed
from ..l10n import tr
from .common import ROW_ID, AppContext, show_error
from .dashboard_card import TODO
from .kind_catalog import UNPLACED_ICON, KindCatalog, element_icon
from .structure_drop import UNPLACED, StructureDrop

__all__ = ["UNPLACED", "StructureTree"]


def _count_text(now: int, then: int) -> str:
    """Measurements of this campaign, beside those of the last one where it had any."""
    return f"{now} / {then}" if then else (str(now) if now else "")


class StructureTree(StructureDrop, QTreeWidget):
    """Dropping elements moves them; dropping rows of the measurement table books them here."""

    chosen = Signal(object)  # an element, None for the whole installation, or UNPLACED
    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.root_id: int | None = None
        self.customer_id: int | None = None  # set when a whole customer is shown, without root
        self.campaign_id: int | None = None
        self.bookable = False  # measurements may move: the campaign is open
        self.measurement_source = None
        self.items: dict[int, QTreeWidgetItem] = {}
        self.collapsed: set[int] = set()
        self._filling = False
        self.setColumnCount(2)
        self.setHeaderLabels([tr("Structure"), tr("Count")])
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.setIconSize(QSize(20, 20))
        self.setIndentation(16)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDropIndicatorShown(True)
        self.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)
        self.currentItemChanged.connect(lambda item, _: self._chosen(item))
        self.itemChanged.connect(self._renamed)
        self.itemCollapsed.connect(lambda item: self.collapsed.add(item.data(0, ROW_ID)))
        self.itemExpanded.connect(lambda item: self.collapsed.discard(item.data(0, ROW_ID)))

    # Building ------------------------------------------------------------

    def show_root(self, root_id: int | None, campaign_id: int | None = None,
                  bookable: bool = False) -> None:
        """One installation, as a campaign sees it, with its counts."""
        same = root_id == self.root_id and self.customer_id is None
        self._show(root_id, None, campaign_id, bookable, same)

    def show_customer(self, customer_id: int | None) -> None:
        """Everything a customer has, every installation at the top."""
        same = customer_id == self.customer_id and self.root_id is None
        self._show(None, customer_id, None, False, same)

    def reload(self) -> None:
        self._show(self.root_id, self.customer_id, self.campaign_id, self.bookable, True)

    def _show(self, root_id, customer_id, campaign_id, bookable, same: bool) -> None:
        keep = self.current_id() if same else None
        if not same:
            self.collapsed.clear()
        self.root_id, self.customer_id = root_id, customer_id
        self.campaign_id, self.bookable = campaign_id, bookable
        self.setColumnHidden(1, campaign_id is None)  # counts exist only in a campaign
        self._filling = True
        self.blockSignals(True)
        self.clear()
        self.items.clear()
        if root_id is not None or customer_id is not None:
            self._build(root_id, customer_id)
        self.blockSignals(False)
        self._filling = False
        self.select(keep if keep in self.items or keep == UNPLACED else root_id)

    def _build(self, root_id: int | None, customer_id: int | None) -> None:
        catalog = KindCatalog(self.app.db)
        if root_id is not None:
            customer_id = self.app.db.asset(root_id)["customer_id"]
        below: dict[int | None, list] = {}
        for row in self.app.db.assets(customer_id):
            below.setdefault(row["parent_id"], []).append(row)
        service = self.app.service
        counts = service.place_counts(self.campaign_id) if self.campaign_id else {}
        before = service.previous_counts(self.campaign_id) if self.campaign_id else {}
        tops = [self.app.db.asset(root_id)] if root_id is not None else below.get(None, [])
        for row in tops:
            top = self._item(row, catalog, counts, before)
            self.addTopLevelItem(top)
            self._add(top, row["id"], below, catalog, counts, before)
            self._dim(top, counts, before)
        if counts.get(None):
            loose = QTreeWidgetItem([tr("No location"), str(counts[None])])
            loose.setIcon(0, element_icon(UNPLACED_ICON))
            loose.setData(0, ROW_ID, UNPLACED)
            loose.setToolTip(0, tr("Measurements not yet assigned to an element."
                                   " Drag them onto an element to assign them."))
            loose.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.addTopLevelItem(loose)
        for asset_id, item in self.items.items():
            item.setExpanded(asset_id not in self.collapsed)

    def _add(self, parent, asset_id, below, catalog, counts, before) -> None:
        for row in below.get(asset_id, ()):
            item = self._item(row, catalog, counts, before)
            parent.addChild(item)
            self._add(item, row["id"], below, catalog, counts, before)

    def _item(self, row, catalog: KindCatalog, counts, before) -> QTreeWidgetItem:
        now, then = counts.get(row["id"], 0), before.get(row["id"], 0)
        item = QTreeWidgetItem([row["name"], _count_text(now, then)])
        item.setIcon(0, catalog.icon(row["kind"]))
        item.setData(0, ROW_ID, row["id"])
        item.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tip = [f"{catalog.label(row['kind'])}: {row['name']}"]
        if row["identifier"]:
            tip.append(tr("Identifier: {identifier}", identifier=row["identifier"]))
        if then:
            tip.append(tr("Last inspection: {before} measurements here, this inspection: {now}",
                          before=then, now=now))
        if now < then:  # measured last time, not yet this time: still to do
            item.setForeground(1, QBrush(QColor(TODO)))
        item.setToolTip(0, "\n".join(tip))
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled
                      | Qt.ItemFlag.ItemIsDropEnabled)
        self.items[row["id"]] = item
        return item

    def _dim(self, item: QTreeWidgetItem, counts, before) -> tuple[int, int]:
        """Returns the branch totals of this campaign and the last one. An element with others
        below counts its whole branch; branches without a measurement step back."""
        asset_id = item.data(0, ROW_ID)
        below = [self._dim(item.child(i), counts, before) for i in range(item.childCount())]
        here, then_here = counts.get(asset_id, 0), before.get(asset_id, 0)
        now = here + sum(n for n, _ in below)
        then = then_here + sum(t for _, t in below)
        if self.campaign_id is not None and not now:
            grey = QBrush(self.palette().color(QPalette.ColorGroup.Disabled,
                                               QPalette.ColorRole.Text))
            item.setForeground(0, grey)
        if asset_id in self.items and below:
            item.setText(1, _count_text(now, then))
            item.setForeground(1, QBrush(QColor(TODO)) if now < then else QBrush())
            item.setToolTip(1, tr("{total} in this branch: {here} here, {below} below",
                                  total=now, here=here, below=now - here) if now else "")
        return now, then

    # Reading -------------------------------------------------------------

    def current_id(self):
        item = self.currentItem()
        return item.data(0, ROW_ID) if item is not None else None

    def selected_ids(self) -> list[int]:
        return [item.data(0, ROW_ID) for item in self.selectedItems()
                if item.data(0, ROW_ID) != UNPLACED]

    def select(self, asset_id) -> None:
        item = self.items.get(asset_id) if asset_id != UNPLACED else next(
            (self.topLevelItem(i) for i in range(self.topLevelItemCount())
             if self.topLevelItem(i).data(0, ROW_ID) == UNPLACED), None)
        if item is not None:
            self.setCurrentItem(item)
            self.scrollToItem(item)

    def _chosen(self, item) -> None:
        asset_id = item.data(0, ROW_ID) if item is not None else None
        self.chosen.emit(None if asset_id == self.root_id else asset_id)

    # Changing ------------------------------------------------------------

    def _renamed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._filling or column != 0 or item.data(0, ROW_ID) == UNPLACED:
            return
        asset_id = item.data(0, ROW_ID)
        if item.text(0) == self.app.db.asset(asset_id)["name"]:
            return
        self._apply(lambda: self.app.service.rename_element(asset_id, item.text(0)))

    def _apply(self, change) -> None:
        """Runs a change, says why one is refused, and rebuilds afterwards."""
        try:
            change()
        except (StructureError, CampaignClosed) as err:
            show_error(self, str(err))
        QTimer.singleShot(0, self._after_change)

    def _after_change(self) -> None:
        self.reload()
        self.changed.emit()

    def update_item(self, asset_id: int) -> None:
        """Name and picture of one element anew, without rebuilding the tree."""
        item, row = self.items.get(asset_id), self.app.db.asset(asset_id)
        if item is not None and row is not None:
            self._filling = True
            item.setText(0, row["name"])
            item.setIcon(0, KindCatalog(self.app.db).icon(row["kind"]))
            self._filling = False
