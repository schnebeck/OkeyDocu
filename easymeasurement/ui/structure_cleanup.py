# EasyMeasurement - easymeasurement/ui/structure_cleanup.py
# Removing elements nothing was ever recorded on, after a look at the list.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem

from .common import ROW_ID, AppContext
from .kind_catalog import KindCatalog
from .overlay import Overlay


class CleanupOverlay(Overlay):
    """Each line is a whole branch: an element and everything below it, all of it empty."""

    def __init__(self, app: AppContext, root_id: int, empty: list[int], parent=None):
        super().__init__("Leere Elemente entfernen", parent, width=560)
        self.ok_button.setText("Entfernen")
        catalog = KindCatalog(app.db)
        intro = QLabel(
            "An diesen Elementen und allem darunter hängt keine Messung, keine Notiz und keine"
            " Datei, in keiner Kampagne." if empty else
            "Hier gibt es keine leeren Elemente. Alles hat Messungen, Notizen oder Dateien."
        )
        intro.setWordWrap(True)
        self.list = QListWidget()
        self.list.setMinimumHeight(220 if empty else 0)
        self.list.setVisible(bool(empty))
        for asset_id in empty:
            asset = app.db.asset(asset_id)
            below = len(app.service.subtree(asset_id)) - 1
            text = app.service.place_path(asset_id, root_id)
            if below:
                text += f"  (mit {below} darunter)"
            item = QListWidgetItem(catalog.icon(asset["kind"]), text)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            item.setData(ROW_ID, asset_id)
            self.list.addItem(item)
        self.list.itemChanged.connect(lambda _: self._update())
        self.body.addWidget(intro)
        self.body.addWidget(self.list)
        if not empty:
            self.ok_button.hide()
            self.cancel_button.setText("Schließen")
        self._update()

    def chosen(self) -> list[int]:
        return [self.list.item(i).data(ROW_ID) for i in range(self.list.count())
                if self.list.item(i).checkState() == Qt.CheckState.Checked]

    def _update(self) -> None:
        count = len(self.chosen())
        self.ok_button.setEnabled(count > 0)
        self.ok_button.setText(f"{count} entfernen" if count else "Entfernen")

    def first_field(self):
        return self.list
