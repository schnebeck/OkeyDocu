# OkeyDocu - okeydocu/ui/elided_label.py
# A label of one line that ends in an ellipsis where its room ends.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A plain label asks for the width of its whole text and pushes its neighbours aside or wraps
into a column of words. This one asks for the whole width, gives way down to a few characters
and never grows in height. What it had to cut waits under the mouse, unless the label has a
tool tip of its own."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSize, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QLabel, QToolTip

LEAST = 8  # characters that stay readable before the ellipsis


class ElidedLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setTextFormat(Qt.TextFormat.PlainText)

    def minimumSizeHint(self) -> QSize:
        hint = super().minimumSizeHint()
        least = self.fontMetrics().averageCharWidth() * LEAST
        return QSize(min(hint.width(), least), hint.height())

    def is_cut(self) -> bool:
        return self.fontMetrics().horizontalAdvance(self.text()) > self.contentsRect().width()

    def event(self, event) -> bool:
        if event.type() == QEvent.Type.ToolTip and not self.toolTip() and self.is_cut():
            QToolTip.showText(event.globalPos(), self.text(), self)
            return True
        return super().event(event)

    def paintEvent(self, event) -> None:
        room = self.contentsRect()
        shown = self.fontMetrics().elidedText(self.text(), Qt.TextElideMode.ElideRight,
                                              room.width())
        QPainter(self).drawText(room, self.alignment(), shown)
