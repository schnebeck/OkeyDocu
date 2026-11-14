# OkeyDocu - okeydocu/ui/wrapping_label.py
# A label that wraps its text and always takes the height the wrapped lines need.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A layout short of height squeezes a wrapped label to its one-line height and cuts the rest.
This label raises its minimum height to what its width needs whenever the width changes."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QSizePolicy


class WrappingLabel(QLabel):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)

    def _fit(self) -> None:
        """The minimum height takes part in `heightForWidth`, so it is cleared first."""
        if self.width() > 0:
            self.setMinimumHeight(0)
            self.setMinimumHeight(self.heightForWidth(self.width()))

    def setText(self, text: str) -> None:
        super().setText(text)
        self._fit()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._fit()
