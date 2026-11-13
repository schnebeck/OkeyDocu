# OkeyDocu - okeydocu/ui/growing_edit.py
# A text field that starts as one line and grows with what is written.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QPlainTextEdit, QSizePolicy

MAX_LINES = 6


class GrowingEdit(QPlainTextEdit):
    """Takes the room of one line until more is written, then scrolls past `MAX_LINES`."""

    def __init__(self, placeholder: str = ""):
        super().__init__()
        # Breeze draws no frame around a view that stands alone in its layout, which leaves a
        # single field in an overlay looking like a bare strip of white.
        self.setProperty("_breeze_force_frame", True)
        self.setPlaceholderText(placeholder)
        self.setTabChangesFocus(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        # Wrapping is laid out after the text changes; the layout tells when the lines change.
        self.document().documentLayout().documentSizeChanged.connect(lambda _: self._fit())
        self.textChanged.connect(self._fit)
        self._fit()

    def refit(self) -> None:
        """After a change of style, which can change the frame around the text."""
        self._fit()

    def _fit(self) -> None:
        lines = max(1, round(self.document().documentLayout().documentSize().height()))
        shown = min(lines, MAX_LINES)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded if lines > MAX_LINES
            else Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        # Frame, style margins and viewport margins: whatever the field has around its text.
        around = self.height() - self.viewport().height() if self.viewport().height() else (
            2 * self.frameWidth() if self.frameShape() != QFrame.Shape.NoFrame else 0)
        padding = 2 * round(self.document().documentMargin())
        height = shown * self.fontMetrics().lineSpacing() + padding + around
        if height != self.maximumHeight():
            self.setFixedHeight(height)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()  # a narrower field wraps into more lines
