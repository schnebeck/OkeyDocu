# EasyMeasurement - easymeasurement/ui/photo_tabs.py
# The photos of a campaign at one place: those of the chosen measurement and those of none.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from .side_panel import SECTION_ALERT

MEASUREMENT, LOOSE = 0, 1
LOOSE_TITLE = "Nicht zugeordnet"


class PhotoTabs(QTabWidget):
    """A photo dragged over a tab opens it, so it can be dropped on the list behind."""

    def __init__(self, gallery: QWidget, stack: QWidget):
        super().__init__()
        self.gallery = gallery
        self.note = QLabel(wordWrap=True)
        self.note.setEnabled(False)
        self.note.hide()
        page = self.measurement_page = QWidget()  # also where a photo is dropped onto
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 4, 0, 0)
        column.addWidget(gallery, 1)
        column.addWidget(self.note)
        column.addStretch(0)
        self.addTab(page, "Messung")
        self.addTab(stack, LOOSE_TITLE)
        self.setDocumentMode(True)
        bar = self.tabBar()
        bar.setChangeCurrentOnDrag(True)
        bar.setAcceptDrops(True)
        self.setTabToolTip(MEASUREMENT, "Die Fotos der gewählten Messung. Ein Foto hierher"
                                         " gezogen gehört dann zu ihr.")
        self.setTabToolTip(LOOSE, "Fotos, die keiner Messung gehören. Sie fehlen im Protokoll,"
                                  " bis sie auf eine Messung gezogen werden.")
        self.loose = 0

    def show_note(self, text: str | None) -> None:
        """Without photos of its own, the measurement's tab says why it is empty."""
        self.note.setText(text or "")
        self.note.setVisible(text is not None)
        self.gallery.setVisible(text is None)

    def set_loose(self, count: int) -> None:
        """The second tab counts its photos and stands out while there are any."""
        self.loose = count
        self.setTabText(LOOSE, f"{LOOSE_TITLE} ({count})" if count else LOOSE_TITLE)
        colour = QColor(SECTION_ALERT) if count else self.palette().color(
            QPalette.ColorRole.WindowText)
        self.tabBar().setTabTextColor(LOOSE, colour)
