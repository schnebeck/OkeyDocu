# EasyMeasurement - easymeasurement/ui/dashboard.py
# The start screen: open and closed campaigns, and the way to everything set up once.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..campaign.seal import SealState
from .campaign_list import heading
from .common import AppContext
from .dashboard_card import CARD_WIDTH, SHOW, CampaignCard
from .dashboard_due import DueSection
from .dashboard_tiles import AdminTiles
from .kind_catalog import KindCatalog

OPEN_SHOWN = 5
CLOSED_SHOWN = 3
FOUND = 9
SPACING = 12
SEAL_WARNINGS = {SealState.TAMPERED: "⚠ Verändert", SealState.NOT_SEALED: "Nicht versiegelt"}
# An empty place among the cards: the dashed outline of the next open campaign.
NEW_CARD_STYLE = """
QPushButton#new-card {
    border: 2px dashed palette(mid); border-radius: 6px; background: palette(base);
}
QPushButton#new-card:hover {
    border-color: palette(highlight); background: palette(alternate-base);
}
"""


def new_card() -> QPushButton:
    button = QPushButton("＋\nNeue Kampagne", objectName="new-card")
    button.setStyleSheet(NEW_CARD_STYLE)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    button.setMinimumSize(CARD_WIDTH, 120)
    button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    font = button.font()
    font.setPointSize(font.pointSize() + 3)
    button.setFont(font)
    return button


class CardSection(QWidget):
    """A heading over a grid of cards that reflows with the width; `last` may close the grid."""

    def __init__(self, title: str, last: QWidget | None = None):
        super().__init__()
        self.title = title
        self.last = last
        self.heading = heading(title, 13)
        self.grid = QGridLayout()
        self.grid.setSpacing(SPACING)
        self.cards: list[CampaignCard] = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING)
        layout.addWidget(self.heading)
        layout.addLayout(self.grid)

    def show_cards(self, cards: list[CampaignCard], total: int, columns: int) -> None:
        self.cards = cards
        more = (f'<span style="font-weight: normal">  ·  {len(cards)} von {total},'
                ' alle stehen links in der Liste</span>')
        self.heading.setText(self.title + (more if total > len(cards) else ""))
        self.setVisible(bool(cards) or self._with_last())
        self.place(columns)

    def _with_last(self) -> bool:
        return self.last is not None and not self.last.isHidden()

    def place(self, columns: int) -> None:
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget is not None and widget not in self.cards and widget is not self.last:
                widget.hide()
                widget.deleteLater()
        shown = self.cards + ([self.last] if self._with_last() else [])
        for number, card in enumerate(shown):
            self.grid.addWidget(card, number // columns, number % columns)
        for column in range(3):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)


class Dashboard(QScrollArea):
    """Stands in the middle while no campaign is chosen."""

    start_requested = Signal()
    due_requested = Signal(int, str, int)  # asset, title, campaign followed up
    master_data_requested = Signal()
    page_requested = Signal(str)
    campaign_requested = Signal(str, int)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.live_id: int | None = None
        self.columns = 3
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.start_button = new_card()
        self.start_button.setToolTip("Kunde und Anlage wählen und die nächste Messung beginnen")
        self.start_button.clicked.connect(self.start_requested)
        top = QVBoxLayout()
        top.addWidget(heading("Messkampagnen", 22))
        top.addWidget(QLabel("Kunde und Anlage wählen, messen, Protokoll bestätigen."))

        self.no_asset = QLabel("Für eine Kampagne braucht es zuerst einen Kunden und eine Anlage.")
        self.no_asset.setWordWrap(True)
        self.master_data_button = QPushButton("Zu den Stammdaten")
        self.master_data_button.clicked.connect(self.master_data_requested)
        missing = QHBoxLayout()
        missing.addWidget(self.no_asset, 1)
        missing.addWidget(self.master_data_button)

        self.search = QLineEdit(placeholderText="Kampagne, Kunde, Ort, Anlage oder Prüfer suchen …")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda _: self._fill())
        self.search.returnPressed.connect(self._open_first)
        self.due = DueSection(app)
        self.due.start_requested.connect(self.due_requested)
        self.open_section = CardSection("Offene Messungen", self.start_button)
        self.closed_section = CardSection("Abgeschlossene Messungen")
        self.empty = QLabel()
        self.empty.setEnabled(False)
        self.tiles = AdminTiles(app)
        self.tiles.requested.connect(self.page_requested)

        content = QWidget()
        column = QVBoxLayout(content)
        column.setContentsMargins(24, 20, 24, 20)
        column.setSpacing(SPACING)
        column.addLayout(top)
        column.addLayout(missing)
        column.addWidget(self.search)
        column.addWidget(self.due)
        column.addWidget(self.open_section)
        column.addWidget(self.closed_section)
        column.addWidget(self.empty)
        column.addSpacing(SPACING)
        column.addWidget(heading("Einrichten und verwalten", 13))
        column.addWidget(self.tiles)
        column.addStretch(1)
        self.setWidget(content)
        self.refresh()

    @property
    def cards(self) -> list[CampaignCard]:
        return self.open_section.cards + self.closed_section.cards

    def refresh(self) -> None:
        has_asset = bool(self.app.db.assets())
        self.start_button.setEnabled(has_asset)
        self.no_asset.setVisible(not has_asset)
        self.master_data_button.setVisible(not has_asset)
        self.summaries = self.app.service.summaries()
        searchable = len(self.summaries) > OPEN_SHOWN
        if not searchable and self.search.text():
            self.search.blockSignals(True)
            self.search.clear()
            self.search.blockSignals(False)
        self.search.setVisible(searchable)
        self.tiles.refresh()
        self.due.refresh()
        self._fill()

    def _fill(self) -> None:
        words = self.search.text().casefold().split()
        self.catalog = KindCatalog(self.app.db)
        self.start_button.setHidden(bool(words))
        self.due.setVisible(not words and self.due.rows.count() > 0)
        found = [s for s in self.summaries if s.matches(words)]
        # The campaign measuring right now is always in reach.
        found.sort(key=lambda summary: summary.id != self.live_id)
        running = [s for s in found if s.is_open]
        closed = [s for s in found if not s.is_open]
        open_limit, closed_limit = (FOUND, FOUND) if words else (OPEN_SHOWN, CLOSED_SHOWN)
        for section, group, limit in ((self.open_section, running, open_limit),
                                      (self.closed_section, closed, closed_limit)):
            cards = [self._card(summary) for summary in group[:limit]]
            section.show_cards(cards, len(group), self.columns)
        self.empty.setText(f"Keine Kampagne passt zu „{self.search.text().strip()}“.")
        self.empty.setVisible(bool(words) and not found)

    def _card(self, summary) -> CampaignCard:
        warning = ""
        if not summary.is_open:
            state = self.app.service.check_seal(summary.id, thorough=False).state
            warning = SEAL_WARNINGS.get(state, "")
        card = CampaignCard(summary, summary.id == self.live_id, warning,
                            self.catalog.icon(summary.kind))
        card.requested.connect(self.campaign_requested)
        return card

    def _open_first(self) -> None:
        if self.cards:
            self.campaign_requested.emit(SHOW, self.cards[0].summary.id)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        columns = max(1, min(3, (self.viewport().width() - 48) // (CARD_WIDTH + SPACING)))
        if columns != self.columns:
            self.columns = columns
            for section in (self.open_section, self.closed_section):
                section.place(columns)
