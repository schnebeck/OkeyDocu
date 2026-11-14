# OkeyDocu - okeydocu/ui/page_window.py
# A page in a window of its own, with the common footer and Close.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Esc, Ctrl+W and the Close button leave the window. A field still being edited is left first,
so a page that stores a field when it is left keeps what was typed."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget

from .. import APP_NAME
from ..l10n import tr
from .footer_bar import FooterBar

MARGIN = 10


class PageWindow(QWidget):
    def __init__(self, page: QWidget, title: str, width: int, height: int):
        super().__init__()
        self.page = page
        self.setWindowTitle(f"{title} – {APP_NAME}")
        self.resize(width, height)
        self.footer = FooterBar()
        self.close_button = self.footer.add(QPushButton(tr("Close")))
        self.close_button.clicked.connect(self.close)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, MARGIN, MARGIN)
        layout.addWidget(page, 1)
        layout.addWidget(self.footer)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Close), self, self.close)

    def keyPressEvent(self, event) -> None:
        """Esc reaches the window only where no field used it, such as to discard an edit."""
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        focused = QApplication.focusWidget()
        if focused is not None and self.isAncestorOf(focused):
            focused.clearFocus()
        super().closeEvent(event)
