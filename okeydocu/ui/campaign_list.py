# OkeyDocu - okeydocu/ui/campaign_list.py
# Every campaign, open and closed, always in reach: by customer and installation, as orders.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..campaign.records import NO_INSTRUMENT
from ..campaign.seal import SealState
from ..l10n import N_, tr
from .campaign_items import SEPARATOR, CampaignDelegate, campaign_icon, campaign_lines
from .common import ROW_ID, AppContext
from .kind_catalog import CUSTOMER_ICON, KindCatalog, element_icon

LIVE_MARK = "● "
GROUP_KEY = Qt.ItemDataRole.UserRole + 1  # ("customer" or "asset", id) on a heading line
SEAL_MARKS = {
    SealState.TAMPERED: N_("⚠ CHANGED"),
    SealState.NOT_SEALED: N_("not sealed"),
}


class CampaignList(QWidget):
    """One click shows a campaign. Measuring in it takes a double click.

    Looking around must not take the instrument away from the campaign it serves.
    """

    chosen = Signal(int)
    resume_requested = Signal(int)
    home_requested = Signal()
    menu_requested = Signal(int, QPoint)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.live_id: int | None = None
        self.home_button = QPushButton(QIcon.fromTheme("go-home"), tr("Overview"))
        self.home_button.setToolTip(tr("Back to the overview with the campaigns worked on last"))
        self.home_button.clicked.connect(self.home_requested)
        self.new_button = QPushButton(tr("New campaign …"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(10)
        self.tree.setItemDelegate(CampaignDelegate(self.tree))
        self.items: dict[int, QTreeWidgetItem] = {}
        self.folded: set[tuple] = set()  # customers and installations folded by hand
        self.tree.itemCollapsed.connect(lambda item: self._remember_fold(item, True))
        self.tree.itemExpanded.connect(lambda item: self._remember_fold(item, False))
        self.tree.itemSelectionChanged.connect(self._chosen)
        # Not itemActivated: with the single click setting of Plasma, that fires on
        # every click, and looking at a campaign would connect to the instrument.
        self.tree.itemDoubleClicked.connect(self._double_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._context_menu)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.home_button)
        layout.addWidget(self.new_button)
        layout.addWidget(self.tree, 1)
        self.refresh()

    def _group(self, parent, text: str, icon: QIcon, key: tuple) -> QTreeWidgetItem:
        """A customer or an installation: open unless it was folded, never chosen itself."""
        group = QTreeWidgetItem([text])
        group.setIcon(0, icon)
        group.setFlags(Qt.ItemFlag.ItemIsEnabled)
        group.setData(0, GROUP_KEY, key)
        parent.addChild(group)
        group.setExpanded(key not in self.folded)
        return group

    def refresh(self) -> None:
        """Customers by name, their installations by place, and on each its orders: the open
        ones first, then the newest."""
        keep = self.current()
        self.tree.blockSignals(True)
        self.tree.clear()
        self.items.clear()
        counts = self.app.service.measurement_counts()
        catalog = KindCatalog(self.app.db)
        grouped: dict[int, dict[int, list]] = {}
        rows = sorted(self.app.service.campaigns(), key=lambda row: row["status"] != "open")
        for row in rows:
            asset = self.app.db.asset(row["asset_id"])
            grouped.setdefault(asset["customer_id"], {}).setdefault(asset["id"], []).append(row)
        top = self.tree.invisibleRootItem()
        for customer in self.app.db.customers():
            assets = grouped.get(customer["id"])
            if not assets:
                continue
            holder = self._group(top, customer["name"], element_icon(CUSTOMER_ICON),
                                 ("customer", customer["id"]))
            bold = holder.font(0)
            bold.setBold(True)
            holder.setFont(0, bold)
            places = {asset_id: self.app.service.place_path(asset_id) for asset_id in assets}
            for asset_id in sorted(assets, key=lambda a: places[a].casefold()):
                kind = self.app.db.asset(asset_id)["kind"]
                place = self._group(holder, places[asset_id], catalog.icon(kind),
                                    ("asset", asset_id))
                for row in assets[asset_id]:
                    place.addChild(self._item(row, counts.get(row["id"], 0)))
        if keep in self.items:
            self.tree.setCurrentItem(self.items[keep])
        self.tree.blockSignals(False)

    def _item(self, row, count: int) -> QTreeWidgetItem:
        is_open = row["status"] == "open"
        item = QTreeWidgetItem([self._text(row, count)])
        item.setData(0, ROW_ID, row["id"])
        item.setIcon(0, campaign_icon(row))
        resumable = is_open and row["driver"] not in NO_INSTRUMENT
        hint = tr("Double-click: continue measuring with the instrument")
        item.setToolTip(0, row["title"] + ("\n" + hint if resumable else ""))
        self.items[row["id"]] = item
        return item

    def _remember_fold(self, item: QTreeWidgetItem, folded: bool) -> None:
        key = item.data(0, GROUP_KEY)
        if key is not None:
            (self.folded.add if folded else self.folded.discard)(key)

    def update_campaign(self, campaign_id: int) -> None:
        """A single reading must not cost a look at every seal in the list."""
        item = self.items.get(campaign_id)
        if item is not None:
            row = self.app.service.campaign(campaign_id)
            count = self.app.service.measurement_counts().get(campaign_id, 0)
            item.setText(0, self._text(row, count))

    def _text(self, row, count: int) -> str:
        """The order with its job and contact; the time and the count tell apart two that
        share title and day. The installation is the line it stands under."""
        mark = LIVE_MARK if row["id"] == self.live_id else ""
        if row["status"] != "open":
            mark = self._seal_mark(row)
        return campaign_lines(row, count, mark)

    def _seal_mark(self, row) -> str:
        state = self.app.service.check_seal(row["id"], thorough=False).state
        if state is SealState.UNVERIFIED and not row["seal_mac"]:
            return tr("Seal without key") + SEPARATOR
        mark = SEAL_MARKS.get(state)
        return tr(mark) + SEPARATOR if mark else ""

    def current(self) -> int | None:
        item = self.tree.currentItem()
        return item.data(0, ROW_ID) if item is not None else None

    def select(self, campaign_id: int | None) -> None:
        self.tree.blockSignals(True)
        if campaign_id in self.items:
            item = self.items[campaign_id]
            self.tree.setCurrentItem(item)
            parent = item.parent()
            while parent is not None:  # the campaign on screen is never folded away
                parent.setExpanded(True)
                self._remember_fold(parent, False)
                parent = parent.parent()
        else:
            self.tree.setCurrentItem(None)
            self.tree.clearSelection()
        self.tree.blockSignals(False)

    def _chosen(self) -> None:
        campaign = self.current()
        if campaign is not None:
            self.chosen.emit(campaign)

    def _context_menu(self, position) -> None:
        item = self.tree.itemAt(position)
        campaign = item.data(0, ROW_ID) if item is not None else None
        if campaign is not None:
            self.menu_requested.emit(campaign, self.tree.viewport().mapToGlobal(position))

    def _double_clicked(self, item: QTreeWidgetItem) -> None:
        campaign = item.data(0, ROW_ID)
        if campaign is not None:
            self.resume_requested.emit(campaign)
