# EasyMeasurement - easymeasurement/ui/overlay.py
# Input that lies over the window instead of opening another one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QEvent, QEventLoop, QRect, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..l10n import tr

MARGIN = 24
SCRIM = QColor(0, 0, 0, 120)


class Overlay(QWidget):
    """A card over the dimmed window. Used like a dialog: `if overlay.exec(): ...`.

    The work stays in view behind it, a live reading still arrives, and no window
    manager has to place anything. Nothing here closes on a stray click: an input
    is only left by a decision. Enter takes the main button, Esc leaves.
    """

    def __init__(self, title: str, parent: QWidget | None = None, width: int = 520):
        self.host = parent.window() if parent is not None else None
        super().__init__(self.host)
        self.hide()
        self.card_width = width
        self.accepted = False
        self._loop: QEventLoop | None = None
        self._blocked: list[QWidget] = []

        self.card = QFrame(self, objectName="overlayCard")
        self.card.setStyleSheet(
            "#overlayCard { background: palette(window); border: 1px solid palette(mid);"
            " border-radius: 8px; }"
        )
        self.card.installEventFilter(self)
        heading = QLabel(title)
        font = heading.font()
        font.setPointSize(font.pointSize() + 4)
        font.setBold(True)
        heading.setFont(font)
        self.body = QVBoxLayout()
        self.hint = QLabel()  # says what is still missing, so a grey button explains itself
        self.hint.setWordWrap(True)
        self.ok_button = QPushButton(tr("Save"))
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton(tr("Cancel"))
        self.cancel_button.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(self.hint, 1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.ok_button)
        column = QVBoxLayout(self.card)
        column.setContentsMargins(20, 16, 20, 16)
        column.setSpacing(12)
        column.addWidget(heading)
        column.addLayout(self.body, 1)
        column.addLayout(buttons)
        if self.host is None:  # no window to lie over
            outer = QVBoxLayout(self)
            outer.addWidget(self.card)

    # Like a dialog -------------------------------------------------------

    def exec(self) -> int:
        self._open()
        self._loop = QEventLoop()
        self._loop.exec()
        self._loop = None
        self._close()
        return int(self.accepted)

    def accept(self) -> None:
        self.accepted = True
        self._leave()

    def reject(self) -> None:
        self.accepted = False
        self._leave()

    def _leave(self) -> None:
        if self._loop is not None:
            self._loop.quit()

    def _open(self) -> None:
        if self.host is not None:
            # Everything else steps back, so Tab and the menus cannot leave the card.
            self._blocked = [
                widget for widget in self.host.findChildren(
                    QWidget, options=Qt.FindChildOption.FindDirectChildrenOnly
                )
                if widget is not self and widget.isVisible() and widget.isEnabled()
            ]
            for widget in self._blocked:
                widget.setEnabled(False)
            self.host.installEventFilter(self)
            self.setGeometry(self.host.rect())
        self.show()
        self.raise_()
        self._place()
        self.first_field().setFocus()

    def _close(self) -> None:
        if self.host is not None:
            self.host.removeEventFilter(self)
            for widget in self._blocked:
                widget.setEnabled(True)
        self.hide()
        self.deleteLater()

    def first_field(self) -> QWidget:
        """What the cursor starts in."""
        return self.ok_button

    # Placing -------------------------------------------------------------

    def _place(self) -> None:
        if self.host is None:
            return
        width = min(self.card_width, self.width() - 2 * MARGIN)
        wanted = self.card.heightForWidth(width)
        height = wanted if wanted > 0 else self.card.sizeHint().height()
        height = min(height, self.height() - 2 * MARGIN)
        self.card.setGeometry(QRect(
            (self.width() - width) // 2, (self.height() - height) // 2, width, height
        ))

    def resizeEvent(self, event) -> None:
        self._place()
        super().resizeEvent(event)

    def eventFilter(self, watched, event) -> bool:
        if watched is self.host:
            if event.type() == QEvent.Type.Resize:
                self.setGeometry(self.host.rect())
            elif event.type() == QEvent.Type.Close:
                self.reject()
        elif watched is self.card and event.type() == QEvent.Type.LayoutRequest:
            self._place()  # a field appeared, the card grows with it
        return False

    def paintEvent(self, event) -> None:
        if self.host is not None:
            QPainter(self).fillRect(self.rect(), SCRIM)

    # Keys and mouse ------------------------------------------------------

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()  # Ctrl+N and the like belong to the window behind
            return True
        return super().event(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.ok_button.isEnabled():
                self.ok_button.click()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event) -> None:
        event.accept()  # the dimmed window takes no clicks
