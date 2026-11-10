# EasyMeasurement - easymeasurement/ui/place_files.py
# Notes and files at an element, with those of the last inspection ready to take over.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPalette
from PySide6.QtWidgets import QListWidgetItem, QPushButton

from .attachment_list import SHOWN_ROWS, AttachmentList
from .common import ROW_ID, AppContext

EARLIER = Qt.ItemDataRole.UserRole + 40  # set on an entry of the last inspection


class PlaceFiles(AttachmentList):
    """Entries of the last inspection stand greyed below the own ones until taken over."""

    def __init__(self, app: AppContext, target_name: str):
        super().__init__(app, target_name)
        self.take_button = QPushButton("Übernehmen")
        self.take_button.setToolTip("Den gewählten Eintrag der letzten Prüfung in diese Kampagne"
                                    " holen. Die abgeschlossene Prüfung bleibt unverändert.")
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
            day = datetime.fromisoformat(previous["closed_at"])
            colour = self.palette().color(QPalette.ColorRole.PlaceholderText)
            font = QFont(self.list.font())
            font.setItalic(True)
            for row in earlier:
                name = row["text"] if row["kind"] == "comment" else row["original_name"]
                item = QListWidgetItem(f"{name}  ·  {day:%d.%m.%Y}")
                item.setForeground(colour)
                item.setFont(font)
                item.setToolTip(f"Aus der Prüfung vom {day:%d.%m.%Y}. „Übernehmen“ holt ihn"
                                " in diese Kampagne, ein Doppelklick zeigt ihn.")
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
