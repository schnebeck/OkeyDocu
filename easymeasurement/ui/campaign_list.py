# EasyMeasurement - easymeasurement/ui/campaign_list.py
# Every campaign, open and closed, always in reach.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPalette
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..campaign.records import NO_INSTRUMENT
from ..campaign.seal import SealState
from ..l10n import N_, moment, plural, tr
from .common import ROW_ID, AppContext

LIVE_MARK = "● "
SEPARATOR = "  ·  "
SEAL_MARKS = {
    SealState.TAMPERED: N_("⚠ CHANGED"),
    SealState.NOT_SEALED: N_("not sealed"),
}


def heading(text: str, size: int = 18) -> QLabel:
    label = QLabel(text)
    font = label.font()
    font.setPointSize(size)
    font.setBold(True)
    label.setFont(font)
    return label


def count_text(count: int) -> str:
    return plural(count, "{count} measurement", "{count} measurements")


class CampaignDelegate(QStyledItemDelegate):
    """The title stands out, the lines below it only tell campaigns apart."""

    PADDING = 4

    def sizeHint(self, option, index) -> QSize:
        size = super().sizeHint(option, index)
        return QSize(size.width(), size.height() + 2 * self.PADDING)

    def paint(self, painter, option, index) -> None:
        title, *details = (index.data() or "").split("\n")
        if not details:
            super().paint(painter, option, index)
            return
        item = QStyleOptionViewItem(option)
        self.initStyleOption(item, index)
        item.text = ""
        style = item.widget.style() if item.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, item, painter, item.widget)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        role = QPalette.ColorRole.HighlightedText if selected else QPalette.ColorRole.Text
        painter.save()
        painter.setPen(option.palette.color(role))
        font = option.font
        line = option.fontMetrics.lineSpacing()
        top = option.rect.top() + self.PADDING
        left, width = option.rect.left() + 4, option.rect.width() - 8
        for number, text in enumerate([title, *details]):
            font.setBold(number == 0)
            painter.setFont(font)
            painter.setOpacity(1.0 if number == 0 or selected else 0.7)
            shown = painter.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, width)
            painter.drawText(QRect(left, top + number * line, width, line),
                             Qt.AlignmentFlag.AlignVCenter, shown)
        painter.restore()


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
        self.running = self._group(tr("Open measurements"))
        self.closed = self._group(tr("Completed measurements"))
        self.items: dict[int, QTreeWidgetItem] = {}
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

    def _group(self, title: str) -> QTreeWidgetItem:
        group = QTreeWidgetItem([title])
        group.setFlags(Qt.ItemFlag.ItemIsEnabled)
        font = group.font(0)
        font.setBold(True)
        group.setFont(0, font)
        self.tree.addTopLevelItem(group)
        group.setExpanded(True)
        return group

    def refresh(self) -> None:
        keep = self.current()
        self.tree.blockSignals(True)
        for group in (self.running, self.closed):
            group.takeChildren()
        self.items.clear()
        counts = self.app.service.measurement_counts()
        for row in self.app.service.campaigns():
            is_open = row["status"] == "open"
            item = QTreeWidgetItem([self._text(row, counts.get(row["id"], 0))])
            item.setData(0, ROW_ID, row["id"])
            resumable = is_open and row["driver"] not in NO_INSTRUMENT
            hint = tr("Double-click: continue measuring with the instrument")
            item.setToolTip(0, row["title"] + ("\n" + hint if resumable else ""))
            (self.running if is_open else self.closed).addChild(item)
            self.items[row["id"]] = item
        self.running.setHidden(self.running.childCount() == 0)
        self.closed.setHidden(self.closed.childCount() == 0)
        if keep in self.items:
            self.tree.setCurrentItem(self.items[keep])
        self.tree.blockSignals(False)

    def update_campaign(self, campaign_id: int) -> None:
        """A single reading must not cost a look at every seal in the list."""
        item = self.items.get(campaign_id)
        if item is not None:
            row = self.app.service.campaign(campaign_id)
            count = self.app.service.measurement_counts().get(campaign_id, 0)
            item.setText(0, self._text(row, count))

    def _text(self, row, count: int) -> str:
        """Two campaigns may share title and day, so the time and the count tell them apart."""
        asset = self.app.db.asset(row["asset_id"])
        since = datetime.fromisoformat(row["started_at"])
        mark = LIVE_MARK if row["id"] == self.live_id else ""
        if row["status"] != "open":
            mark = self._seal_mark(row)
        details = f"{moment(since)}{SEPARATOR}{count_text(count)}"
        return f"{mark}{row['title']}\n{asset['name']}\n{details}"

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
            self.tree.setCurrentItem(self.items[campaign_id])
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
