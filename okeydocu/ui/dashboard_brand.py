# OkeyDocu - okeydocu/ui/dashboard_brand.py
# The program's name, version and tagline at the top of the start screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .. import APP_NAME, TAGLINE, __version__

ICON_PX = 44


class Brand(QWidget):
    """Icon, name and version on one line, the tagline beneath."""

    def __init__(self):
        super().__init__()
        self.icon = QLabel()
        icon = QGuiApplication.windowIcon()
        if icon.isNull():
            self.icon.hide()
        else:
            self.icon.setPixmap(icon.pixmap(ICON_PX, ICON_PX))
        self.name = QLabel(APP_NAME)
        font = self.name.font()
        font.setPointSize(font.pointSize() + 9)
        font.setBold(True)
        self.name.setFont(font)
        self.version = QLabel(__version__)
        self.version.setEnabled(False)
        self.tagline = QLabel(TAGLINE)
        font = self.tagline.font()
        font.setItalic(True)
        self.tagline.setFont(font)

        title = QHBoxLayout()
        title.setSpacing(8)
        title.addWidget(self.name)
        title.addWidget(self.version, 0, Qt.AlignmentFlag.AlignBottom)
        title.addStretch(1)
        words = QVBoxLayout()
        words.setSpacing(0)
        words.addLayout(title)
        words.addWidget(self.tagline)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        layout.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addLayout(words, 1)
