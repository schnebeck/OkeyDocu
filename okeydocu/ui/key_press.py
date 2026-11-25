# OkeyDocu - okeydocu/ui/key_press.py
# The press of a key on the drawn panel, shown for a moment.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A key of the drawn panel that was clicked goes down and comes up again: its face lights
up and draws in from its edge, then eases back within a quarter of a second. The mark lies
over the key as a widget of its own and lets every click through to the panel below."""

from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

PRESS_MS = 260
MARGIN = 4  # room around the key for the mark's edge
TRAVEL = 3.0  # pixels the face draws in at the deepest point


class KeyPress(QWidget):
    def __init__(self, panel: QWidget):
        super().__init__(panel)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.depth = 0.0  # 1 at the moment of the press, 0 when the key is up again
        self.run = QVariantAnimation(self, startValue=1.0, endValue=0.0, duration=PRESS_MS)
        self.run.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.run.valueChanged.connect(self._sink)
        self.run.finished.connect(self.hide)
        self.hide()

    def press(self, key: QRectF) -> None:
        """Shows the key at `key`, in the panel's coordinates, being pressed."""
        self.run.stop()
        self.setGeometry(key.toAlignedRect().adjusted(-MARGIN, -MARGIN, MARGIN, MARGIN))
        self.depth = 1.0
        self.show()
        self.raise_()
        self.run.start()

    def _sink(self, depth) -> None:
        self.depth = float(depth)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inset = MARGIN + TRAVEL * self.depth
        face = QRectF(self.rect()).adjusted(inset, inset, -inset, -inset)
        painter.setPen(QPen(QColor(255, 255, 255, int(230 * self.depth)), 1.6))
        painter.setBrush(QColor(255, 255, 255, int(70 * self.depth)))
        painter.drawRoundedRect(face, 6, 6)
