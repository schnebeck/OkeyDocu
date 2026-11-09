# EasyMeasurement - easymeasurement/ui/board.py
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
    QSplitter,
    QSplitterHandle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

GUTTER = 8  # between the main blocks of a window, so they do not run into each other
EDGE = 8  # between the blocks and the window's border


def control_height() -> int:
    """A line edit is the tallest thing in a bar; buttons beside it take on its height."""
    return QLineEdit().sizeHint().height()


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
        self.row.setContentsMargins(6, 4, 6, 4)
        self.row.setSpacing(4)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 1 if ruled else 0)
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
            painter.fillRect(0, self.height() - 1, self.width(), 1, rule_colour(self))


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


RULE_GAP = 4  # background between the left pane, often ending in its scroll bar, and the line


class _Rule(QSplitterHandle):
    """Background, then a thin line at the right edge, where the next pane begins."""

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.palette().color(QPalette.ColorRole.Window))
        painter.fillRect(self.width() - 1, 0, 1, self.height(), rule_colour(self))


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

    The frame is painted rather than left to the style, some styles hardly show one.
    """

    def __init__(self, name: str, *panes: QWidget, head: QWidget | None = None):
        super().__init__()
        self.splitter = _Splitter(objectName=name)
        self.splitter.setHandleWidth(RULE_GAP + 1)
        self.splitter.setChildrenCollapsible(False)
        for widget in panes:
            self.splitter.addWidget(widget)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        if head is not None:
            layout.addWidget(head)
        layout.addWidget(self.splitter, 1)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setPen(rule_colour(self))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
