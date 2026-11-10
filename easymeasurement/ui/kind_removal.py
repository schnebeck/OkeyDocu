# EasyMeasurement - easymeasurement/ui/kind_removal.py
# Deleting a kind: the elements using it take another one, nothing is left without a kind.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel

from ..l10n import plural, tr
from .common import AppContext
from .kind_catalog import KindCatalog
from .overlay import Overlay

FALLBACK_KIND = "measuring_point"


class RemoveKindOverlay(Overlay):
    """Values noted under features of the old kind stay with the elements, hidden."""

    def __init__(self, app: AppContext, key: str, parent=None):
        catalog = KindCatalog(app.db)
        super().__init__(tr("Delete kind “{kind}”", kind=catalog.label(key)), parent)
        self.ok_button.setText(tr("Delete"))
        used = app.db.kind_usage(key)
        self.instead = QComboBox()
        for kind in sorted(catalog.all, key=lambda k: k.label.casefold()):
            if kind.key != key:
                self.instead.addItem(catalog.icon(kind.key), kind.label, kind.key)
        self.instead.setCurrentIndex(max(self.instead.findData(FALLBACK_KIND), 0))
        if used:
            text = plural(used, "{count} element is of this kind. It gets the one chosen here"
                                " instead. Its name, measurements and feature values are kept.",
                          "{count} elements are of this kind. They get the one chosen here"
                          " instead. Their names, measurements and feature values are kept.")
        else:
            text = tr("No element is of this kind. It simply disappears from the choice.")
        intro = QLabel(text)
        intro.setWordWrap(True)
        self.body.addWidget(intro)
        form = QFormLayout()
        form.addRow(tr("Instead"), self.instead)
        self.body.addLayout(form)
        self.instead.setVisible(bool(used))
        form.labelForField(self.instead).setVisible(bool(used))
        self.used = used

    def replacement(self) -> str | None:
        return self.instead.currentData() if self.used else None

    def first_field(self):
        return self.instead if self.used else self.ok_button
