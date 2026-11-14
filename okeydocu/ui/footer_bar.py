# OkeyDocu - okeydocu/ui/footer_bar.py
# The row at the foot of every window and card: a hint on the left, the buttons on the right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Buttons stand side by side, the main one last; only where the footer is too narrow for them
in a row do they stack, in the same order, each as wide as the footer. The hint then stands
above them. Buttons added at the start stand on the left, before the hint."""

from __future__ import annotations

from PySide6.QtWidgets import QBoxLayout, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from .wrapping_label import WrappingLabel

HINT_ROOM = 160  # the hint keeps at least this much beside the buttons


class FooterBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hint = WrappingLabel()
        self.leading: list[QPushButton] = []
        self.buttons: list[QPushButton] = []
        self.start = QHBoxLayout()
        self.start.setContentsMargins(0, 0, 0, 0)
        self.row = QBoxLayout(QBoxLayout.Direction.LeftToRight)
        self.row.setContentsMargins(0, 0, 0, 0)
        self.outer = QBoxLayout(QBoxLayout.Direction.LeftToRight, self)
        self.outer.setContentsMargins(0, 0, 0, 0)
        self.outer.addLayout(self.start)
        self.outer.addWidget(self.hint, 1)
        self.outer.addLayout(self.row)
        self.stacked = False

    def add(self, button: QPushButton) -> QPushButton:
        """At the right end; the main button is added last."""
        self.buttons.append(button)
        self.row.addWidget(button)
        return button

    def add_leading(self, button: QPushButton) -> QPushButton:
        """At the left end, such as Back in a sequence of steps."""
        self.leading.append(button)
        self.start.addWidget(button)
        return button

    def _needed(self) -> int:
        shown = [b for b in self.leading + self.buttons if not b.isHidden()]
        spacing = self.row.spacing() * max(len(shown) - 1, 0)
        return sum(b.sizeHint().width() for b in shown) + spacing + HINT_ROOM

    def _arrange(self) -> None:
        stack = self.width() < self._needed()
        if stack == self.stacked:
            return
        self.stacked = stack
        vertical, horizontal = QBoxLayout.Direction.TopToBottom, QBoxLayout.Direction.LeftToRight
        self.outer.setDirection(vertical if stack else horizontal)
        self.row.setDirection(vertical if stack else horizontal)
        self.start.setDirection(vertical if stack else horizontal)
        self.updateGeometry()  # the card around it takes the new height

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._arrange()

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        widest = max((b.sizeHint().width() for b in self.leading + self.buttons), default=0)
        hint.setWidth(widest)
        return hint


def footed(content: QWidget, footer: FooterBar, margin: int = 12) -> QWidget:
    """A window holding `content` with the footer below it."""
    window = QWidget()
    column = QVBoxLayout(window)
    column.setContentsMargins(0, 0, 0, margin)
    column.addWidget(content, 1)
    row = QHBoxLayout()
    row.setContentsMargins(margin, 0, margin, 0)
    row.addWidget(footer)
    column.addLayout(row)
    return window
