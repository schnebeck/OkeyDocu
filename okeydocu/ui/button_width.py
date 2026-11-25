# OkeyDocu - okeydocu/ui/button_width.py
# One width for a button whose text changes, so it and its neighbours stay in place.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QPushButton


def widest(button: QPushButton, texts) -> int:
    """The width `button` needs for the longest of `texts`."""
    widths = []
    for text in texts:
        button.setText(text)
        widths.append(button.sizeHint().width())
    return max(widths)
