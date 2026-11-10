# EasyMeasurement - easymeasurement/ui/measurement_detail.py
# What the selected measurement holds, and what may be done to it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import QFileDialog, QListWidgetItem, QMessageBox

from ..campaign.photo_marks import ROLES
from ..campaign.service import MANUAL
from .common import AppContext, function_short, selected_id
from .photo_gallery import PHOTO_ID, PHOTO_PATH
from .photo_preview import PhotoPreview
from .photo_shared import shared_thumbs

THUMB = 150


def _waiting() -> QPixmap:
    pixmap = QPixmap(THUMB, THUMB * 3 // 4)
    pixmap.fill(QColor("#d5d8dc"))
    return pixmap
# Where a double click in the table puts the cursor, by column.
FIELD_OF_COLUMN = {4: "location", 5: "function", 6: "values", 8: "verdict"}


def row_is_open(app: AppContext, row) -> bool:
    return app.service.campaign(row["campaign_id"])["status"] == "open"


def pick_images(parent) -> list[Path]:
    files, _ = QFileDialog.getOpenFileNames(
        parent, "Fotos wählen", "", "Bilder (*.jpg *.jpeg *.png *.heic *.JPG *.JPEG *.PNG)"
    )
    return [Path(f) for f in files]


def capture_text(row) -> str:
    if row["source"] == MANUAL:
        return "manuell"
    return "Import" if row["source"].startswith("import:") else "Messgerät"


class MeasurementDetail:
    """Shows the selected row beside the table, where it is corrected in place."""

    hide_empty_gallery = False  # true where no heading says the empty space is for photos

    def _selected_row(self):
        measurement_id = selected_id(self.table)
        if measurement_id is None:
            return None
        return self.app.db.one("SELECT * FROM measurements WHERE id=?", measurement_id)

    def _show_detail(self) -> None:
        row = self._selected_row()
        editor = self.editor
        leaving = editor.row is not None and (row is None or row["id"] != editor.row["id"])
        if leaving and editor.dirty:
            # Moving on takes the edits along. The table is rebuilt once this signal is over.
            editor.blockSignals(True)
            editor.apply()
            editor.blockSignals(False)
            QTimer.singleShot(0, self._after_change)
        self.gallery.clear()
        self._update_actions(row)
        editable = bool(row) and row_is_open(self.app, row)
        editor.show_row(row, editable, capture_text(row) if row else "")
        self.gallery.setVisible(not self.hide_empty_gallery)
        self.gallery.removable = editable
        if row is None:
            return
        service, thumbs = self.app.service, shared_thumbs()
        for photo in service.photos_of(row["id"]):
            path = str(service.photo_path(row["campaign_id"], photo["file_name"]))
            # A picture not read yet arrives through the cache's `ready`, so selecting stays quick.
            item = QListWidgetItem(QIcon(thumbs.get(path) or _waiting()), photo["original_name"])
            item.setData(PHOTO_PATH, path)
            item.setData(PHOTO_ID, photo["id"])
            if photo["role"]:
                item.setText(f"{ROLES[photo['role']]} · {item.text()}")
            item.setToolTip(photo["taken_at"] or "Zeitpunkt unbekannt")
            self.gallery.addItem(item)
        self.gallery.setVisible(self.gallery.count() > 0 or not self.hide_empty_gallery)

    def _preview_photo(self, item: QListWidgetItem) -> None:
        PhotoPreview(item.text(), item.toolTip(), Path(item.data(PHOTO_PATH)), self, self.app,
                     item.data(PHOTO_ID)).exec()
        self._show_detail()  # a role changed shows in the gallery

    def _unpin_photo(self, photo_id: int) -> None:
        """The photo leaves the measurement and waits among the photos of no measurement."""
        self.app.service.stack_photo(photo_id)
        self._after_change()

    def _thumb_ready(self, path: str) -> None:
        for index in range(self.gallery.count()):
            item = self.gallery.item(index)
            if item.data(PHOTO_PATH) == path:
                item.setIcon(QIcon(shared_thumbs().get(path)))

    def _update_actions(self, row) -> None:
        editable = bool(row) and row_is_open(self.app, row)
        for action in (self.edit_action, self.delete_action, self.photo_action):
            action.setEnabled(editable)

    # Actions -------------------------------------------------------------

    def _after_change(self) -> None:
        self.refresh()
        self.changed.emit()

    def _edit_measurement(self, field: str = "comment") -> None:
        self.edit_requested.emit()
        self.editor.focus_field(field)

    def _by_key(self, slot) -> None:
        if self.edit_action.isEnabled():
            slot()

    def _cell_double_clicked(self, _row: int, column: int) -> None:
        if self.edit_action.isEnabled():
            self._edit_measurement(FIELD_OF_COLUMN.get(column, "comment"))

    def _delete_measurement(self) -> None:
        row = self._selected_row()
        when = datetime.fromisoformat(row["local_time"])
        answer = QMessageBox.question(
            self, "Messung löschen",
            f"Messung {function_short(row['function'])} vom {when:%d.%m.%Y %H:%M:%S} löschen?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.editor.show_row(None, False)
            self.app.service.delete_measurement(row["id"])
            self._after_change()

    def _add_photo(self) -> None:
        row = self._selected_row()
        for path in pick_images(self):
            self.app.service.add_photo(row["id"], path)
        self._after_change()
