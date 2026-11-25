# OkeyDocu - okeydocu/ui/framed.py
# A block of the window inside the thin frame the board draws, with the board's inset.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""What belongs together stands in one frame. Every frame of a column has the same edges and
keeps what it holds the same distance off them, so the left and the right ends of all blocks
form two lines down the window."""

from __future__ import annotations

from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .board import UNIT, rule_colour
from .pixel_lines import LINE, frame

TEXT = 2  # bare text stands this much further in, where the faces of buttons and fields begin


class Framed(QWidget):
    """`box` takes the rows of the block. Blocks standing on each other without room between
    them read as the rows of one table: a block without `top` continues the one above it,
    a `joined` one is continued by the one below."""

    def __init__(self, top: bool = True, joined: bool = False):
        super().__init__()
        self.top, self.joined = top, joined
        self.box = QVBoxLayout(self)
        self.box.setSpacing(UNIT)
        self._inset()

    def set_top(self, top: bool) -> None:
        """Whether the block begins the frame or continues the block above it."""
        if top != self.top:
            self.top = top
            self._inset()
            self.update()

    def _inset(self) -> None:
        above = (LINE if self.top else 0) + UNIT
        self.box.setContentsMargins(LINE + UNIT, above, LINE + UNIT, LINE + UNIT)

    def paintEvent(self, event) -> None:
        frame(QPainter(self), self.rect(), rule_colour(self), self.top, self.joined)
