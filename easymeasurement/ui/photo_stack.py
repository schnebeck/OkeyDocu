# EasyMeasurement - easymeasurement/ui/photo_stack.py
# Photos without an assignment: drag them to a measurement, put them back, or delete them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QPoint, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPalette
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListView,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..store import CampaignClosed
from .common import AppContext, ROW_ID, show_error
from .photo_preview import PhotoPreview
from .photo_shared import accept_photo_drops, shared_thumbs, start_photo_drag

ICON = QSize(96, 72)
CELL = QSize(112, 112)
EMPTY_TEXT = "Der Stapel ist leer. Hier landen Fotos, die von einer Messung gelöst wurden."
HELP_TEXT = "Auf eine Messung ziehen."
READ_ONLY_TEXT = "Abgeschlossene Kampagne: nur ansehen."


class StackList(QListWidget):
    """The thumbnails. A drag carries the photo id, an empty list says what it is for."""

    def __init__(self):
        super().__init__()
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setIconSize(ICON)
        self.setGridSize(CELL)
        self.setMovement(QListView.Movement.Static)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setWordWrap(True)
        self.setDragEnabled(True)
        self.setMinimumHeight(CELL.height() + 8)

    def startDrag(self, actions) -> None:
        item = self.currentItem()
        if item is not None:
            pixmap = item.icon().pixmap(ICON)
            start_photo_drag(self, item.data(ROW_ID), pixmap)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        if self.count() == 0:
            painter = QPainter(self.viewport())
            painter.setPen(self.palette().color(QPalette.ColorRole.PlaceholderText))
            flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap
            painter.drawText(self.viewport().rect().adjusted(12, 0, -12, 0), flags, EMPTY_TEXT)


class PhotoStack(QWidget):
    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.campaign_id: int | None = None
        self.locked = False
        self.closed = False
        self.rows: dict[int, object] = {}
        self.by_path: dict[str, QListWidgetItem] = {}
        self.thumbs = shared_thumbs()
        self.list = StackList()
        self.hint = QLabel(HELP_TEXT, wordWrap=True)
        self.hint.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.back_button = QPushButton("Zurück auf die Zeitleiste")
        self.delete_button = QPushButton("Löschen …")
        buttons = QHBoxLayout()
        buttons.addWidget(self.back_button)
        buttons.addStretch(1)
        buttons.addWidget(self.delete_button)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self.list, 1)
        column.addWidget(self.hint)
        column.addLayout(buttons)
        self.target = accept_photo_drops(self.list.viewport(), self._take_dropped)
        self.back_button.clicked.connect(self.put_back)
        self.delete_button.clicked.connect(self.delete_selected)
        self.list.itemSelectionChanged.connect(self._update_buttons)
        self.list.itemDoubleClicked.connect(self._open)
        self.thumbs.ready.connect(self._thumb_ready)
        self._update_buttons()

    @property
    def count(self) -> int:
        return self.list.count()

    @property
    def read_only(self) -> bool:
        return self.locked or self.closed

    def show_campaign(self, campaign_id: int) -> None:
        self.campaign_id = campaign_id
        self.refresh()

    def refresh(self) -> None:
        if self.campaign_id is None:
            return
        service = self.app.service
        self.closed = service.campaign(self.campaign_id)["status"] != "open"
        kept = {item.data(ROW_ID) for item in self.list.selectedItems()}
        self.rows = {row["id"]: row for row in service.stacked_photos(self.campaign_id)}
        self.list.clear()
        self.by_path = {}
        for photo_id, row in self.rows.items():
            item = QListWidgetItem(self._caption(row))
            item.setData(ROW_ID, photo_id)
            item.setToolTip(row["original_name"])
            path = service.photo_path(self.campaign_id, row["file_name"])
            self.by_path[str(path)] = item
            self._give_icon(item, path)
            self.list.addItem(item)
            item.setSelected(photo_id in kept)
        self._apply_lock()

    def set_read_only(self, read_only: bool) -> None:
        self.locked = read_only
        self._apply_lock()

    @staticmethod
    def _caption(row) -> str:
        if not row["taken_at"]:
            return "ohne Zeit"
        return f"{datetime.fromisoformat(row['taken_at']):%H:%M:%S}"

    def _give_icon(self, item: QListWidgetItem, path: Path) -> None:
        pixmap = self.thumbs.get(path)
        if pixmap is not None:
            item.setIcon(QIcon(pixmap))

    def _thumb_ready(self, path: str) -> None:
        if path in self.by_path:
            self._give_icon(self.by_path[path], Path(path))

    def _apply_lock(self) -> None:
        self.list.setDragEnabled(not self.read_only)
        self.target.enabled = not self.read_only
        self.hint.setText(READ_ONLY_TEXT if self.read_only else HELP_TEXT)
        self._update_buttons()

    def _selected(self) -> list[int]:
        return [item.data(ROW_ID) for item in self.list.selectedItems()]

    def _update_buttons(self) -> None:
        chosen = self._selected()
        timed = [photo for photo in chosen if self.rows[photo]["taken_at"]]
        self.back_button.setEnabled(bool(timed) and not self.read_only)
        self.delete_button.setEnabled(bool(chosen) and not self.read_only)
        if chosen and not timed and not self.read_only:
            self.hint.setText("Ohne Aufnahmezeit geht es nur per Ziehen auf eine Messung.")
        elif not self.read_only:
            self.hint.setText(HELP_TEXT)

    # Changing data --------------------------------------------------------

    def _write(self, work, photos: list[int]) -> None:
        try:
            for photo in photos:
                work(photo)
        except CampaignClosed:
            self.refresh()
            show_error(self, "Die Kampagne ist abgeschlossen, Fotos lassen sich nicht mehr ändern.")
            return
        self.refresh()
        self.changed.emit()

    def put_back(self) -> None:
        timed = [photo for photo in self._selected() if self.rows[photo]["taken_at"]]
        if timed and not self.read_only:
            self._write(self.app.service.return_to_timeline, timed)

    def delete_selected(self) -> None:
        chosen = self._selected()
        if not chosen or self.read_only:
            return
        name = self.rows[chosen[0]]["original_name"]
        what = f"Das Foto {name}" if len(chosen) == 1 else f"{len(chosen)} Fotos"
        answer = QMessageBox.question(
            self, "Foto löschen",
            f"{what} endgültig löschen?\n\nDie Bilddatei wird entfernt. "
            "Das lässt sich nicht rückgängig machen.",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._write(self.app.service.delete_photo, chosen)

    def _take_dropped(self, photo_id: int, pos: QPoint) -> None:
        if photo_id not in self.rows:
            self._write(self.app.service.stack_photo, [photo_id])

    def _open(self, item: QListWidgetItem) -> None:
        row = self.rows[item.data(ROW_ID)]
        path = self.app.service.photo_path(self.campaign_id, row["file_name"])
        taken = row["taken_at"].replace("T", " ") if row["taken_at"] else "ohne Aufnahmezeit"
        PhotoPreview(row["original_name"], f"Aufgenommen {taken}", path, self, self.app,
                     item.data(ROW_ID)).exec()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
        else:
            super().keyPressEvent(event)
