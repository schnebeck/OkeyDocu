# EasyMeasurement - easymeasurement/ui/side_panel.py
# The panels beside the measurements: all can be seen at once, each can be folded.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)



class Section(QWidget):
    folded = Signal()

    def __init__(self, title: str, content: QWidget):
        super().__init__()
        self.title = title
        self.content = content
        self.toggle = QToolButton()
        self.toggle.setCheckable(True)
        self.toggle.setChecked(True)
        self.toggle.setAutoRaise(True)
        self.toggle.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle.setStyleSheet("QToolButton { font-weight: bold; text-align: left; }")
        self.toggle.toggled.connect(self._toggled)
        # The content stands in a little from the heading, as text on a page does.
        self.body = QWidget()
        inset = QVBoxLayout(self.body)
        inset.setContentsMargins(8, 2, 2, 8)
        inset.addWidget(content)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toggle)
        layout.addWidget(self.body, 1)
        self.set_count(None)
        self._show_arrow()

    def set_count(self, count: int | None) -> None:
        self.toggle.setText(self.title if count is None else f"{self.title} ({count})")

    @property
    def expanded(self) -> bool:
        return self.toggle.isChecked()

    def _show_arrow(self) -> None:
        self.toggle.setArrowType(
            Qt.ArrowType.DownArrow if self.expanded else Qt.ArrowType.RightArrow
        )

    def _toggled(self, expanded: bool) -> None:
        self.body.setVisible(expanded)
        self._show_arrow()
        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred if expanded else QSizePolicy.Policy.Maximum,
        )
        self.folded.emit()


class SidePanel(QScrollArea):
    """Sections share the height. When they need more than there is, the panel scrolls
    instead of pressing a section below the size its fields need."""

    def __init__(self):
        super().__init__()
        self.sections: list[Section] = []
        inner = QWidget()
        self.column = QVBoxLayout(inner)
        self.column.setContentsMargins(0, 0, 0, 0)
        self.column.addStretch(0)  # takes the room once everything is folded
        self.setWidget(inner)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def minimumSizeHint(self) -> QSize:
        """As narrow as the sections allow, but free in height: that is what scrolls."""
        width = self.widget().minimumSizeHint().width() + self.verticalScrollBar().sizeHint().width()
        return QSize(width, 0)

    def add(self, title: str, content: QWidget) -> Section:
        section = Section(title, content)
        section.folded.connect(self._share_room)
        self.column.insertWidget(len(self.sections), section, 1)
        self.sections.append(section)
        return section

    def _share_room(self) -> None:
        for index, section in enumerate(self.sections):
            self.column.setStretch(index, 1 if section.expanded else 0)
