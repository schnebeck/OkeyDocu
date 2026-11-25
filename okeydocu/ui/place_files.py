# OkeyDocu - okeydocu/ui/place_files.py
# Notes and files at an element, photos dropped there, and what the last inspection left.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QListWidgetItem, QPushButton

from ..l10n import day, tr
from .attachment_list import SHOWN_ROWS, AttachmentList
from .common import ROW_ID, AppContext
from .photo_shared import dropped_photo
from .photo_to_place import place_photo

EARLIER = Qt.ItemDataRole.UserRole + 40  # set on an entry of the last inspection


class PlaceFiles(AttachmentList):
    """Entries of the last inspection stand greyed below the own ones until taken over."""

    photo_taken = Signal()  # a photo of the campaign lies here now and left the photos

    def __init__(self, app: AppContext, target_name: str):
        super().__init__(app, target_name)
        self.take_button = QPushButton(tr("Take over"))
        self.take_button.setToolTip(tr("Fetch the chosen entry of the last inspection into this"
                                       " campaign. The ended campaign stays unchanged."))
        self.take_button.clicked.connect(self._take_over)
        self.layout().itemAt(self.layout().count() - 1).layout().insertWidget(1, self.take_button)
        self._update()

    def show_target(self, campaign_id: int | None, editable: bool = False, **target) -> None:
        super().show_target(campaign_id, editable, **target)
        asset_id = target.get("asset_id")
        if not (campaign_id and editable and asset_id is not None):
            self._update()
            return
        previous = self.app.service.earlier_campaign(campaign_id)
        earlier = self.app.service.earlier_attachments(campaign_id, asset_id)
        if earlier:
            closed = day(datetime.fromisoformat(previous["closed_at"]))
            colour = self.palette().color(QPalette.ColorRole.PlaceholderText)
            font = QFont(self.list.font())
            font.setItalic(True)
            for row in earlier:
                name = row["text"] if row["kind"] == "comment" else row["original_name"]
                item = QListWidgetItem(f"{name}  ·  {closed}")
                item.setForeground(colour)
                item.setFont(font)
                item.setToolTip(tr("From the inspection of {day}. “Take over” fetches it into"
                                   " this campaign, a double-click shows it.", day=closed))
                item.setData(ROW_ID, row["id"])
                item.setData(EARLIER, True)
                self.list.addItem(item)
            shown = min(self.list.count(), SHOWN_ROWS)
            self.list.setFixedHeight(shown * (self.list.fontMetrics().height() + 8) + 4)
            self.list.show()
        self._update()

    def _chosen_earlier(self) -> QListWidgetItem | None:
        item = self.list.currentItem()
        return item if item is not None and item.data(EARLIER) else None

    def _update(self) -> None:
        super()._update()
        if not hasattr(self, "take_button"):
            return
        has_earlier = any(self.list.item(i).data(EARLIER) for i in range(self.list.count()))
        own = sum(not self.list.item(i).data(EARLIER) for i in range(self.list.count()))
        self.take_button.setVisible(self.editable and has_earlier)
        self.take_button.setEnabled(self._chosen_earlier() is not None)
        self.empty.setVisible(self.editable and own == 0 and not has_earlier)
        self.remove_button.setVisible(self.editable and own > 0)
        chosen = self.list.currentItem()
        self.remove_button.setEnabled(chosen is not None and not chosen.data(EARLIER))

    def _take_over(self) -> None:
        item = self._chosen_earlier()
        if item is not None:
            self.app.service.take_over_attachment(
                self.campaign_id, item.data(ROW_ID), self.target["asset_id"])
            self._after_change()

    def _remove(self) -> None:
        """An entry of the sealed inspection is never removed from here."""
        if self._chosen_earlier() is None:
            super()._remove()

    # A photo of the campaign ------------------------------------------------

    def _takes_photo(self, event) -> bool:
        return (self.editable and self.target.get("asset_id") is not None
                and dropped_photo(event.mimeData()) is not None)

    def dragEnterEvent(self, event) -> None:
        if self._takes_photo(event):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        if not self._takes_photo(event):
            super().dropEvent(event)
            return
        photo = dropped_photo(event.mimeData())
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        # Once the drag is over: laying it here may ask a question first.
        QTimer.singleShot(0, lambda: self.take_photo(photo))

    def take_photo(self, photo_id: int) -> None:
        if place_photo(self, self.app.service, photo_id, self.target["asset_id"]):
            self._after_change()
            self.photo_taken.emit()
