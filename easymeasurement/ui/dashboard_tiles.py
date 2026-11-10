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

from ..l10n import N_, plural, tr
from .common import AppContext
from .dashboard_card import dim

ICON_SIZE = 32
MASTER_DATA, PLANS, TEMPLATES, ARCHIVE, USERS, INSTRUMENT = (
    "master_data", "plans", "templates", "archive", "users", "instrument",
)
# Key, title, theme icon, fallback icon, what it is for.
_TILES = (
    (MASTER_DATA, N_("Master data"), "x-office-address-book",
     QStyle.StandardPixmap.SP_DirHomeIcon, N_("Customers, installations and their parts")),
    (PLANS, N_("Test plans"), "view-list-details", QStyle.StandardPixmap.SP_FileDialogListView,
     N_("Which measurements in which order")),
    (TEMPLATES, N_("Report templates"), "document-edit",
     QStyle.StandardPixmap.SP_FileDialogDetailedView,
     N_("Layout, logos and texts of the reports")),
    (ARCHIVE, N_("Report archive"), "folder-documents", QStyle.StandardPixmap.SP_DirIcon,
     N_("Generated and signed reports")),
    (USERS, N_("Users"), "system-users", QStyle.StandardPixmap.SP_DialogYesButton,
     N_("Inspectors with signature and certificate")),
    (INSTRUMENT, N_("Instrument"), "network-bluetooth", QStyle.StandardPixmap.SP_DriveNetIcon,
     N_("Pair Bluetooth, detect USB")),
)


class Tile(QPushButton):
    """A button with a bold name and a line of figures; the labels let clicks through."""

    def __init__(self, title: str, icon: QIcon, purpose: str):
        super().__init__()
        self.setToolTip(purpose)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(60)
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
            title = tr(title)
            purpose = tr(purpose)
            tile = Tile(title, icon, purpose)
            tile.setAccessibleName(f"{title}: {purpose}")
            tile.clicked.connect(lambda _=False, key=key: self.requested.emit(key))
            self.buttons[key] = tile
            self.purposes[key] = purpose
        self._place(3)
        self.refresh()

    def _place(self, columns: int) -> None:
        if columns == self.columns:
            return
        self.columns = columns
        while self.grid.count():
            self.grid.takeAt(0)
        for number, tile in enumerate(self.buttons.values()):
            self.grid.addWidget(tile, number // columns, number % columns)
        for column in range(len(self.buttons)):
            self.grid.setColumnStretch(column, 1 if column < columns else 0)

    def _needed(self) -> int:
        """The width the widest tile needs to show its texts uncut."""
        return max(tile.layout().sizeHint().width() for tile in self.buttons.values())

    def _fitting(self, width: int) -> int:
        """All in one row where every text fits, else rows of three, two or one."""
        needed = self._needed()
        spacing = self.grid.spacing()
        for columns in (len(self.buttons), 3, 2):
            if columns * needed + (columns - 1) * spacing <= width:
                return columns
        return 1

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._place(self._fitting(self.width()))

    def refresh(self) -> None:
        db = self.app.db
        figures = {
            MASTER_DATA: plural(len(db.customers()), "{count} customer", "{count} customers")
            + ", " + plural(len(db.assets()), "{count} element", "{count} elements"),
            PLANS: plural(len(db.plans()), "{count} plan", "{count} plans"),
            TEMPLATES: plural(len(db.templates()), "{count} template", "{count} templates"),
            ARCHIVE: plural(len(self.app.archive.reports()), "{count} report", "{count} reports"),
            USERS: plural(len(db.users()), "{count} inspector", "{count} inspectors"),
        }
        for key, tile in self.buttons.items():
            tile.figure.setText(figures.get(key, self.purposes[key]))
        needed = self._needed()
        for tile in self.buttons.values():
            tile.setMinimumWidth(needed)
        self._place(self._fitting(self.width()))
