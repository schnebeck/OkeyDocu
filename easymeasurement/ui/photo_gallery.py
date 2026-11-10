# EasyMeasurement - easymeasurement/ui/photo_gallery.py
# The photos of the chosen measurement; one dragged onto another row belongs there instead.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QAbstractItemView, QListWidget

from .photo_shared import start_photo_drag

PHOTO_PATH = Qt.ItemDataRole.UserRole + 1
PHOTO_ID = Qt.ItemDataRole.UserRole + 2


class PhotoGallery(QListWidget):
    """Thumbnails in a grid. Dragging one carries the photo, not a copy of the item."""

    def __init__(self, thumb: int):
        super().__init__()
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QPixmap(thumb, thumb).size())
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setToolTip("Doppelklick zeigt das Foto groß; auf eine andere Zeile der Tabelle"
                        " gezogen, gehört es zu jener Messung.")

    def startDrag(self, actions) -> None:
        item = self.currentItem()
        if item is not None and item.data(PHOTO_ID) is not None:
            start_photo_drag(self, item.data(PHOTO_ID), item.icon().pixmap(self.iconSize()))
