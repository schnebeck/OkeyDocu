# OkeyDocu - okeydocu/ui/board.py
# Panes side by side in one frame, each with a bar of the same height, so they read as one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPointF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPalette, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractScrollArea,
    QFrame,
    QHBoxLayout,
    QLineEdit,
    QMenu,
    QPushButton,
    QSplitter,
    QSplitterHandle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .pixel_lines import LINE, device_rect, frame, line_width, rule_below

GUTTER = 8  # between the main blocks of a window, so they do not run into each other
EDGE = 8  # between the blocks and the window's border
UNIT = 4  # between a frame and what stands in it; controls in a row keep twice that apart


def control_height() -> int:
    """A line edit is the tallest thing in a bar; buttons beside it take on its height."""
    return QLineEdit().sizeHint().height()


def row_height() -> int:
    """A button is the tallest thing in a row of a block; a row that holds only text takes
    the same height, so rows taking each other's place leave what is below where it is."""
    return QPushButton("x").sizeHint().height()


def rule_colour(widget: QWidget) -> QColor:
    """Lines drawn from the text colour, faint: visible on light and dark themes alike."""
    colour = QColor(widget.palette().color(QPalette.ColorRole.WindowText))
    colour.setAlpha(70)
    return colour


def _arrow(colour: QColor) -> QIcon:
    pixmap = QPixmap(9, 9)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(colour)
    painter.drawPolygon(QPolygonF([QPointF(0.5, 2.5), QPointF(8.5, 2.5), QPointF(4.5, 7)]))
    painter.end()
    return QIcon(pixmap)


def menu_button(text: str, tip: str) -> QToolButton:
    """A button that opens its menu at once, with the arrow after the text like a combo box.

    The icon goes right by turning the button's direction; the menu keeps the usual one.
    """
    button = QToolButton()
    button.setText(text)
    button.setToolTip(tip)
    button.setIcon(_arrow(button.palette().color(QPalette.ColorRole.ButtonText)))
    button.setIconSize(QSize(9, 9))
    button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    button.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    button.setStyleSheet("QToolButton::menu-indicator { image: none; width: 0; }")
    button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
    button.setMenu(QMenu(button))
    button.menu().setLayoutDirection(Qt.LayoutDirection.LeftToRight)
    return button


class Strip(QWidget):
    """A row on the window's grey, above the white of the views."""

    def __init__(self, row: QHBoxLayout | None = None, ruled: bool = True):
        super().__init__()
        self.ruled = ruled  # a line below closes the head of the board off
        self.row = row or QHBoxLayout()
        self.row.setContentsMargins(UNIT, UNIT, UNIT, UNIT)
        self.row.setSpacing(2 * UNIT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, LINE if ruled else 0)
        layout.addLayout(self.row)

    def even_out(self) -> None:
        """Every control gets one height, in every pane alike."""
        height = control_height()
        for index in range(self.row.count()):
            widget = self.row.itemAt(index).widget()
            if widget is not None:
                widget.setFixedHeight(height)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))
        if self.ruled:
            rule_below(painter, self.rect(), rule_colour(self))


def pane(bar: Strip, view: QAbstractScrollArea) -> QWidget:
    """A bar above a view; the view loses its own frame, the board draws one around all."""
    view.setFrameShape(QFrame.Shape.NoFrame)
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(0)
    layout.addWidget(bar)
    layout.addWidget(view, 1)
    return widget


class _Rule(QSplitterHandle):
    """A thin line and nothing beside it, so the lines of the panes run into it. A handle
    this thin is grabbed a few pixels to either side as well.

    In a window scaled by a fraction the handle covers a pixel more in some places. The
    line then spreads over all of them, lighter, and keeps its weight."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))
        area = device_rect(painter, self.rect())
        upright = self.orientation() == Qt.Orientation.Horizontal
        across = area.width() if upright else area.height()
        colour = rule_colour(self)
        colour.setAlphaF(colour.alphaF() * min(1.0, line_width(painter) / max(across, 1)))
        painter.fillRect(self.rect(), colour)


class _Splitter(QSplitter):
    def createHandle(self) -> QSplitterHandle:
        return _Rule(self.orientation(), self)


class _Gap(QSplitterHandle):
    """Only the window's background: the room between blocks is space, not a bar."""

    def paintEvent(self, event) -> None:
        QPainter(self).fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))


class GutterSplitter(QSplitter):
    """Main blocks of a window side by side, kept apart by plain space that can be dragged."""

    def __init__(self, *args, width: int = GUTTER, **kwargs):
        super().__init__(*args, **kwargs)
        self.setHandleWidth(width)

    def createHandle(self) -> QSplitterHandle:
        return _Gap(self.orientation(), self)


class Board(QWidget):
    """A drawn frame; a line across the top if there is one, then panes that share a rule.
    Every line inside runs from one line to another: the rules from the head to the frame,
    the lines below the bars from the frame to a rule.

    The frame is painted rather than left to the style, some styles hardly show one.
    """

    def __init__(self, name: str, *panes: QWidget, head: QWidget | None = None,
                 top: bool = True):
        super().__init__()
        self.top = top  # without one, the board continues the block standing on it
        self.splitter = _Splitter(objectName=name)
        self.splitter.setHandleWidth(LINE)
        self.splitter.setChildrenCollapsible(False)
        for widget in panes:
            self.splitter.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(LINE, LINE if top else 0, LINE, LINE)
        layout.setSpacing(0)
        if head is not None:
            layout.addWidget(head)
        layout.addWidget(self.splitter, 1)

    def paintEvent(self, event) -> None:
        frame(QPainter(self), self.rect(), rule_colour(self), self.top)
