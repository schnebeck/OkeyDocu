# EasyMeasurement - easymeasurement/ui/attachment_list.py
# Notes, images and PDFs on a measurement or a place, added by button or by dropping files.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from ..campaign.attachments import ATTACHMENT_KINDS, AttachmentError
from .common import ROW_ID, AppContext, show_error
from .growing_edit import GrowingEdit
from .overlay import Overlay

SHOWN_ROWS = 4
_ICONS = {
    "comment": QStyle.StandardPixmap.SP_FileDialogDetailedView,
    "image": QStyle.StandardPixmap.SP_FileIcon,
    "pdf": QStyle.StandardPixmap.SP_FileIcon,
}
_THEME_ICONS = {"comment": "view-pim-notes", "image": "image-x-generic", "pdf": "application-pdf"}
FILE_FILTER = "Bilder und PDF (*.pdf *.jpg *.jpeg *.png *.heic *.PDF *.JPG *.JPEG *.PNG)"


class NoteOverlay(Overlay):
    def __init__(self, target: str, parent=None):
        super().__init__(f"Notiz zu {target}", parent)
        self.ok_button.setText("Hinzufügen")
        self.text = GrowingEdit("Was festgehalten werden soll, es erscheint im Protokoll")
        self.text.textChanged.connect(
            lambda: self.ok_button.setEnabled(bool(self.text.toPlainText().strip()))
        )
        self.body.addWidget(self.text)
        self.ok_button.setEnabled(False)

    def first_field(self):
        return self.text


class AttachmentList(QWidget):
    """What lies on one target. `image_handler`, if given, takes images instead of the list."""

    changed = Signal()

    def __init__(self, app: AppContext, target_name: str, image_handler=None, notes=True):
        super().__init__()
        self.notes = notes
        self.app = app
        self.target_name = target_name
        self.image_handler = image_handler
        self.campaign_id: int | None = None
        self.target: dict = {}
        self.editable = False
        self.setAcceptDrops(True)
        self.list = QListWidget()
        self.list.itemActivated.connect(self._open)
        self.list.currentRowChanged.connect(lambda _: self._update())
        self.empty = QLabel("Dateien hierher ziehen oder anhängen.")
        self.empty.setWordWrap(True)
        self.empty.setEnabled(False)
        self.note_button = QPushButton("Notiz …")
        self.note_button.clicked.connect(self.add_note)
        self.file_button = QPushButton("Datei …")
        self.file_button.clicked.connect(self._pick_files)
        self.remove_button = QPushButton("Entfernen")
        self.remove_button.clicked.connect(self._remove)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.note_button, self.file_button, self.remove_button):
            buttons.addWidget(button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list)
        layout.addWidget(self.empty)
        layout.addLayout(buttons)
        self.show_target(None)

    def show_target(self, campaign_id: int | None, editable: bool = False, **target) -> None:
        """`target` is `measurement_id=…` or `asset_id=…`."""
        self.campaign_id, self.target, self.editable = campaign_id, target, editable
        self.list.clear()
        rows = self.app.service.attachments(campaign_id, **target) if campaign_id else []
        for row in rows:
            text = row["text"] if row["kind"] == "comment" else row["original_name"]
            icon = QIcon.fromTheme(
                _THEME_ICONS[row["kind"]], self.style().standardIcon(_ICONS[row["kind"]])
            )
            item = QListWidgetItem(icon, text)
            item.setToolTip((row["text"] or row["original_name"])
                            + ("\nDoppelklick: öffnen" if row["file_name"] else ""))
            item.setData(ROW_ID, row["id"])
            self.list.addItem(item)
        rows_shown = min(max(len(rows), 1), SHOWN_ROWS)
        self.list.setFixedHeight(rows_shown * (self.list.fontMetrics().height() + 8) + 4)
        self.list.setVisible(bool(rows))
        self._update()

    def _update(self) -> None:
        self.empty.setVisible(self.list.count() == 0 and self.editable)
        self.note_button.setVisible(self.editable and self.notes)
        self.file_button.setVisible(self.editable)
        self.remove_button.setVisible(self.editable and self.list.count() > 0)
        self.remove_button.setEnabled(self.list.currentRow() >= 0)

    # Adding --------------------------------------------------------------

    def add_note(self) -> None:
        overlay = NoteOverlay(self.target_name, self)
        if overlay.exec():
            self.app.service.add_comment(
                self.campaign_id, overlay.text.toPlainText().strip(), **self.target
            )
            self._after_change()

    def _pick_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Datei anhängen", "", FILE_FILTER)
        self.add_files([Path(f) for f in files])

    def add_files(self, paths: list[Path]) -> None:
        refused = []
        for path in paths:
            kind = ATTACHMENT_KINDS.get(path.suffix.lower())
            try:
                if kind == "image" and self.image_handler is not None:
                    self.image_handler(path)
                else:
                    self.app.service.add_attachment(self.campaign_id, path, **self.target)
            except AttachmentError as err:
                refused.append(str(err))
        if len(refused) < len(paths):
            self._after_change()
        if refused:
            show_error(self, "\n".join(refused))

    def _after_change(self) -> None:
        self.show_target(self.campaign_id, self.editable, **self.target)
        self.changed.emit()

    # Using ---------------------------------------------------------------

    def _open(self, item: QListWidgetItem) -> None:
        row = self.app.db.one("SELECT * FROM attachments WHERE id=?", item.data(ROW_ID))
        if row["file_name"]:
            path = self.app.service.attachment_path(row["campaign_id"], row["file_name"])
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def _remove(self) -> None:
        item = self.list.currentItem()
        if item is not None:
            self.app.service.delete_attachment(item.data(ROW_ID))
            self._after_change()

    def dragEnterEvent(self, event) -> None:
        if self.editable and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = [Path(url.toLocalFile()) for url in event.mimeData().urls() if url.isLocalFile()]
        event.acceptProposedAction()
        self.add_files(paths)
