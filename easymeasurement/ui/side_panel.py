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
    QLabel,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)



SECTION_ALERT = "#d35400"


class Section(QWidget):
    folded = Signal()

    def __init__(self, title: str, content: QWidget, grows: bool = True):
        super().__init__()
        self.title = title
        self.grows = grows  # takes a share of free height while it is open
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
        self.empty = False
        self.placeholder = QLabel()  # stands for content that has nothing to show
        self.placeholder.setWordWrap(True)
        self.placeholder.setEnabled(False)
        self.placeholder.hide()
        inset = QVBoxLayout(self.body)
        inset.setContentsMargins(8, 2, 2, 8)
        inset.addWidget(content)
        inset.addWidget(self.placeholder)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.toggle)
        layout.addWidget(self.body, 1)
        self.set_count(None)
        self._show_arrow()

    def set_empty(self, text: str | None) -> None:
        """With nothing to show, a short line instead of the content, and no share of room."""
        self.empty = text is not None
        self.placeholder.setText(text or "")
        self.placeholder.setVisible(self.empty)
        self.content.setVisible(not self.empty)
        self.folded.emit()

    def set_quiet(self, quiet: bool) -> None:
        """Keeps its content in view but takes no share of the free room."""
        self.empty = quiet
        self.folded.emit()

    def set_count(self, count: int | None) -> None:
        self.toggle.setText(self.title if count is None else f"{self.title} ({count})")

    def set_alert(self, on: bool) -> None:
        """A heading in the warning colour for something still to be done here."""
        colour = f" color: {SECTION_ALERT};" if on else ""
        self.toggle.setStyleSheet(
            f"QToolButton {{ font-weight: bold; text-align: left;{colour} }}")

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
        self.folded.emit()  # the panel shares the room out again


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

    def add(self, title: str, content: QWidget, grows: bool = True) -> Section:
        section = Section(title, content, grows)
        section.folded.connect(self._share_room)
        self.column.insertWidget(len(self.sections), section)
        self.sections.append(section)
        self._share_room()
        return section

    def _share_room(self) -> None:
        """Only open sections with something to show grow; the others keep to their content.

        Free room goes by stretch: to the growing sections, or to the space at the end while
        none grows. A section is never capped at its size hint, which assumes a wider column
        and so fewer lines of wrapped text than the panel shows; its height follows its width.
        """
        growing = False
        for index, section in enumerate(self.sections):
            grows = section.grows and section.expanded and not section.empty
            growing = growing or grows
            self.column.setStretch(index, 1 if grows else 0)
            policy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            policy.setHeightForWidth(True)
            section.setSizePolicy(policy)
        self.column.setStretch(len(self.sections), 0 if growing else 1)
