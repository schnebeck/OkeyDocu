# EasyMeasurement - easymeasurement/ui/campaign_header.py
# The head of the campaign workspace: which campaign, what can be done and what is left.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .campaign_list import heading


class CampaignHeader(QWidget):
    """Says which campaign this is and offers what can be done with it now."""

    tester_requested = Signal()
    edit_requested = Signal()
    home_requested = Signal()
    check_requested = Signal(str)  # a link in the checks: what to look at

    def __init__(self):
        super().__init__()
        self.home_button = QToolButton()
        self.home_button.setIcon(QIcon.fromTheme(
            "go-home", self.style().standardIcon(QStyle.StandardPixmap.SP_DirHomeIcon)))
        self.home_button.setToolTip("Zur Übersicht (Alt+Pos1)")
        self.home_button.setAutoRaise(True)
        self.home_button.clicked.connect(self.home_requested)
        self.title = heading("", 15)
        self.edit_button = QToolButton()
        fallback = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.edit_button.setIcon(QIcon.fromTheme("document-edit", fallback))
        self.edit_button.setAccessibleName("Kampagne bearbeiten")
        self.edit_button.setToolTip("Titel und Anlage ändern")
        self.edit_button.setAutoRaise(True)
        self.edit_button.clicked.connect(self.edit_requested)
        self.details = QLabel()
        self.details.setTextFormat(Qt.TextFormat.RichText)
        self.details.linkActivated.connect(lambda _: self.tester_requested.emit())
        self.resume_button = QPushButton("Messung fortsetzen")
        self.pause_button = QPushButton("Messung unterbrechen")
        self.photos_button = QPushButton("Fotos …")
        self.draft_button = QPushButton("Entwurf ansehen")
        self.draft_button.setToolTip("Das Protokoll, wie es jetzt aussähe. Es ist noch nicht gültig.")
        self.finish_button = QPushButton(QIcon.fromTheme("object-locked"), "Bestätigen …")
        self.finish_button.setToolTip("Abschließen, versiegeln, Protokoll ablegen und signieren."
                                      " Danach lässt sich nichts mehr ändern.")
        # What is left before confirming, with links to the rows concerned.
        self.checks = QLabel()
        self.checks.setTextFormat(Qt.TextFormat.RichText)
        self.checks.linkActivated.connect(self.check_requested)
        self.report_button = QPushButton("Protokoll erstellen …")
        text = QVBoxLayout()
        text.setSpacing(0)
        title = QHBoxLayout()
        title.addWidget(self.home_button)
        title.addWidget(self.title)
        title.addWidget(self.edit_button)
        title.addStretch(1)
        text.addLayout(title)
        text.addWidget(self.details)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.resume_button, self.pause_button, self.photos_button,
                       self.draft_button, self.finish_button, self.report_button):
            buttons.addWidget(button)
            # Shown by the campaign that needs them; hidden pages keep their first layout.
            button.hide()
        side = QVBoxLayout()
        side.setSpacing(2)
        side.addLayout(buttons)
        side.addWidget(self.checks, 0, Qt.AlignmentFlag.AlignRight)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addLayout(text, 1)
        row.addLayout(side)
