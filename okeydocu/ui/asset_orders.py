# OkeyDocu - okeydocu/ui/asset_orders.py
# The orders on an element of the master data: every campaign run against it, and a new one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""An installation exists once, with its structure; each campaign against it is an order of
its own. The list shows them newest first; a double click opens one in the main window."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..l10n import tr
from .campaign_items import CampaignDelegate, campaign_icon, campaign_lines, heading
from .common import ROW_ID, AppContext

SHOWN_ORDERS = 5  # rows the list shows before it scrolls


class AssetOrders(QWidget):
    open_requested = Signal(int)  # a campaign
    new_requested = Signal(int)  # an element to start a campaign on

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.asset_id: int | None = None
        self.list = QListWidget()
        self.list.setItemDelegate(CampaignDelegate(self.list))
        self.list.itemDoubleClicked.connect(lambda item: self.open_requested.emit(
            item.data(ROW_ID)))
        self.list.setToolTip(tr("Double-click: show the campaign"))
        self.empty = QLabel(tr("No campaign has been run on this element yet."))
        self.empty.setWordWrap(True)
        self.empty.setEnabled(False)
        self.new_button = QPushButton(tr("New campaign …"))
        self.new_button.clicked.connect(lambda: self.new_requested.emit(self.asset_id))
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.new_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 0)
        layout.addWidget(heading(tr("Orders"), 11))
        layout.addWidget(self.list)
        layout.addWidget(self.empty)
        layout.addLayout(buttons)

    def show_asset(self, asset_id: int | None) -> None:
        self.asset_id = asset_id
        self.reload()

    def reload(self) -> None:
        self.list.clear()
        rows = self.app.service.campaigns(self.asset_id) if self.asset_id is not None else []
        counts = self.app.service.measurement_counts() if rows else {}
        for row in sorted(rows, key=lambda row: row["status"] != "open"):
            item = QListWidgetItem(campaign_icon(row),
                                   campaign_lines(row, counts.get(row["id"], 0)))
            item.setData(ROW_ID, row["id"])
            self.list.addItem(item)
        shown = min(max(len(rows), 1), SHOWN_ORDERS)
        row_height = self.list.sizeHintForRow(0) if rows else 0
        self.list.setFixedHeight(shown * row_height + 2 * self.list.frameWidth())
        self.list.setVisible(bool(rows))
        self.empty.setVisible(not rows)
