# EasyMeasurement - easymeasurement/ui/dashboard_tiles.py
# Tiles on the start screen for what is set up once and used in every campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from .common import AppContext
from .dashboard_card import dim

TILE_WIDTH = 220
ICON_SIZE = 32
MASTER_DATA, PLANS, TEMPLATES, ARCHIVE, USERS, INSTRUMENT = (
    "master_data", "plans", "templates", "archive", "users", "instrument",
)
# Key, title, theme icon, fallback icon, what it is for.
_TILES = (
    (MASTER_DATA, "Stammdaten", "x-office-address-book", QStyle.StandardPixmap.SP_DirHomeIcon,
     "Kunden, Anlagen und ihre Teile"),
    (PLANS, "Messpläne", "view-list-details", QStyle.StandardPixmap.SP_FileDialogListView,
     "Welche Messungen in welcher Reihenfolge"),
    (TEMPLATES, "Protokollvorlagen", "document-edit",
     QStyle.StandardPixmap.SP_FileDialogDetailedView, "Aufbau, Logos und Texte der Protokolle"),
    (ARCHIVE, "Protokollarchiv", "folder-documents", QStyle.StandardPixmap.SP_DirIcon,
     "Erzeugte und signierte Protokolle"),
    (USERS, "Benutzer", "system-users", QStyle.StandardPixmap.SP_DialogYesButton,
     "Prüfer mit Unterschrift und Zertifikat"),
    (INSTRUMENT, "Messgerät", "network-bluetooth", QStyle.StandardPixmap.SP_DriveNetIcon,
     "Bluetooth koppeln, USB erkennen"),
)


def _plural(count: int, one: str, many: str) -> str:
    return f"1 {one}" if count == 1 else f"{count} {many}"


class Tile(QPushButton):
    """A button with a bold name and a line of figures; the labels let clicks through."""

    def __init__(self, title: str, icon: QIcon, purpose: str):
        super().__init__()
        self.setToolTip(purpose)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(60)
        self.setMinimumWidth(160)
        picture = QLabel()
        picture.setPixmap(icon.pixmap(ICON_SIZE, ICON_SIZE))
        self.name = QLabel(title)
        font = self.name.font()
        font.setBold(True)
        self.name.setFont(font)
        self.figure = dim(QLabel(purpose))
        text = QVBoxLayout()
        text.setSpacing(0)
        text.addWidget(self.name)
        text.addWidget(self.figure)
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 6, 12, 6)
        row.setSpacing(10)
        row.addWidget(picture)
        row.addLayout(text, 1)
        for label in (picture, self.name, self.figure):
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


class AdminTiles(QWidget):
    """Each tile says what is there, so an empty one shows where to begin."""

    requested = Signal(str)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.buttons: dict[str, Tile] = {}
        self.purposes: dict[str, str] = {}
        self.columns = 0
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setSpacing(12)
        for number, (key, title, theme, fallback, purpose) in enumerate(_TILES):
            icon = QIcon.fromTheme(theme, self.style().standardIcon(fallback))
            tile = Tile(title, icon, purpose)
            tile.setAccessibleName(f"{title}: {purpose}")
            tile.clicked.connect(lambda _=False, key=key: self.requested.emit(key))
            self.buttons[key] = tile
            self.purposes[key] = purpose
        self._place(3)
        self.refresh()

    def _place(self, columns: int) -> None:
        """All in one row where the width allows, else in rows of three."""
        if columns == self.columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for number, tile in enumerate(self.buttons.values()):
            self.grid.addWidget(tile, number // columns, number % columns)
        for column in range(len(self.buttons)):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        count = len(self.buttons)
        self._place(count if self.width() >= count * (TILE_WIDTH + 12) else 3)

    def refresh(self) -> None:
        db = self.app.db
        figures = {
            MASTER_DATA: _plural(len(db.customers()), "Kunde", "Kunden") + ", "
            + _plural(len(db.assets()), "Element", "Elemente"),
            PLANS: _plural(len(db.plans()), "Plan", "Pläne"),
            TEMPLATES: _plural(len(db.templates()), "Vorlage", "Vorlagen"),
            ARCHIVE: _plural(len(self.app.archive.reports()), "Protokoll", "Protokolle"),
            USERS: _plural(len(db.users()), "Prüfer", "Prüfer"),
        }
        for key, tile in self.buttons.items():
            tile.figure.setText(figures.get(key, self.purposes[key]))
