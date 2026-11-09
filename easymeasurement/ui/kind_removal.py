# EasyMeasurement - easymeasurement/ui/kind_removal.py
# Deleting a kind: the elements using it take another one, nothing is left without a kind.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel

from .common import AppContext
from .kind_catalog import KindCatalog
from .overlay import Overlay

FALLBACK_KIND = "measuring_point"


class RemoveKindOverlay(Overlay):
    """Values noted under features of the old kind stay with the elements, hidden."""

    def __init__(self, app: AppContext, key: str, parent=None):
        catalog = KindCatalog(app.db)
        super().__init__(f"Typ „{catalog.label(key)}“ löschen", parent)
        self.ok_button.setText("Löschen")
        used = app.db.kind_usage(key)
        self.instead = QComboBox()
        for kind in sorted(catalog.all, key=lambda k: k.label.casefold()):
            if kind.key != key:
                self.instead.addItem(catalog.icon(kind.key), kind.label, kind.key)
        self.instead.setCurrentIndex(max(self.instead.findData(FALLBACK_KIND), 0))
        if used:
            text = (f"{used} Elemente sind von diesem Typ. Sie bekommen stattdessen den hier"
                    " gewählten. Ihre Namen, Messungen und Merkmalswerte bleiben erhalten.")
        else:
            text = "Kein Element ist von diesem Typ. Er verschwindet einfach aus der Auswahl."
        intro = QLabel(text)
        intro.setWordWrap(True)
        self.body.addWidget(intro)
        form = QFormLayout()
        form.addRow("Stattdessen", self.instead)
        self.body.addLayout(form)
        self.instead.setVisible(bool(used))
        form.labelForField(self.instead).setVisible(bool(used))
        self.used = used

    def replacement(self) -> str | None:
        return self.instead.currentData() if self.used else None

    def first_field(self):
        return self.instead if self.used else self.ok_button
