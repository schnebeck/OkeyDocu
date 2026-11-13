# OkeyDocu - okeydocu/ui/edge_drawer.py
# A panel that slides in from the left window edge while the mouse is there.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QVBoxLayout,
    QWidget,
)

from .board import EDGE

LEAVE_POLLS = 4  # polls away from the drawer before it goes, so a quick slip keeps it
POLL_MS = 90


class EdgeDrawer(QFrame):
    """Lies over the left of the page; shown while the mouse is at the edge or on it.

    The pointer is polled rather than tracked: tracking would need every widget below
    to report its moves. A maximised window starts at the screen edge, so pushing the
    mouse against the edge is enough to find it.
    """

    def __init__(self, page: QWidget, width: int = 320):
        super().__init__(page)
        self.page = page
        self.active = False
        self.closing = False
        self._away = 0
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setAutoFillBackground(True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(3, 0)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.setGraphicsEffect(shadow)
        self.column = QVBoxLayout(self)
        self.column.setContentsMargins(EDGE, EDGE, EDGE, EDGE)
        self.resize(width, page.height())
        self.hide()
        self.timer = QTimer(self, interval=POLL_MS)
        self.timer.timeout.connect(self._poll)
        self.motion = QPropertyAnimation(self, b"pos", self)
        self.motion.setDuration(140)
        self.motion.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.motion.finished.connect(self._settled)
        page.installEventFilter(self)

    def hold(self, widget: QWidget) -> None:
        self.column.addWidget(widget)

    def set_active(self, on: bool) -> None:
        self.active = on
        if on:
            self.timer.start()
        else:
            self.timer.stop()
            self.motion.stop()
            self.hide()

    def shown(self) -> bool:
        return self.isVisible() and not self.closing

    def toggle(self) -> None:
        self.close_drawer() if self.shown() else self.open()

    def open(self) -> None:
        if not self.active or self.shown():
            return
        self._fit()
        self.closing, self._away = False, 0
        if not self.isVisible():
            self.move(-self.width(), 0)
            self.show()
        self.raise_()
        self._slide(0)

    def close_drawer(self) -> None:
        if self.shown():
            self.closing = True
            self._slide(-self.width())

    def react(self, point: QPoint, buttons_free: bool = True) -> None:
        """Where the mouse is, in the page's coordinates, opens or closes the drawer."""
        if not self.active:
            return
        within = 0 <= point.y() < self.page.height()
        if not self.shown():
            if buttons_free and within and 0 <= point.x() < EDGE:
                self.open()
            return
        near = self.geometry().adjusted(0, 0, 2 * EDGE, 0).contains(point)
        self._away = 0 if near else self._away + 1
        if self._away >= LEAVE_POLLS:
            self.close_drawer()

    def _poll(self) -> None:
        # A menu opened from the drawer or a dialog keeps everything as it is.
        if (not self.page.window().isActiveWindow() or QApplication.activePopupWidget()
                or QApplication.activeModalWidget() or not self.page.isVisible()):
            return
        free = QApplication.mouseButtons() == Qt.MouseButton.NoButton
        self.react(self.page.mapFromGlobal(QCursor.pos()), free)

    def _slide(self, x: int) -> None:
        self.motion.stop()
        self.motion.setStartValue(self.pos())
        self.motion.setEndValue(QPoint(x, 0))
        self.motion.start()

    def _settled(self) -> None:
        if self.closing:
            self.hide()
            self.closing = False

    def _fit(self) -> None:
        self.resize(self.width(), self.page.height())

    def eventFilter(self, watched, event) -> bool:
        if watched is self.page and event.type() == QEvent.Type.Resize:
            self._fit()
        return False

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.close_drawer()
            return
        super().keyPressEvent(event)
