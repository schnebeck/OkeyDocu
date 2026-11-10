# EasyMeasurement - easymeasurement/ui/guided_pages.py
# The wizard pages for a question and for a note, and asking for a reason.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.plan import PlanStep
from ..l10n import tr
from .growing_edit import GrowingEdit
from .overlay import Overlay

CHOICE_STYLE = (
    "QPushButton { padding: 12px 28px; }"
    "QPushButton:checked { background: palette(highlight); color: palette(highlighted-text); }"
)


def _mnemonic(button: QPushButton):
    """The key underlined in the button's text, which answers without the mouse."""
    sequence = QKeySequence.mnemonic(button.text())
    return sequence[0].key() if not sequence.isEmpty() else None


def _big_label(point_size_step: int) -> QLabel:
    label = QLabel()
    label.setWordWrap(True)
    font = label.font()
    font.setPointSize(font.pointSize() + point_size_step)
    label.setFont(font)
    return label


class CheckPage(QWidget):
    """One question. The expected answer goes on at once, any other waits for a comment."""

    chosen = Signal(str)
    edited = Signal()
    next_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.question = _big_label(5)
        self.question.setStyleSheet("font-weight: bold;")
        self.text = QLabel()
        self.text.setWordWrap(True)
        self.buttons = {
            "yes": QPushButton(tr("&Yes")), "no": QPushButton(tr("&No")),
            "skip": QPushButton(tr("&Skip")),
        }
        self.keys = {_mnemonic(button): choice for choice, button in self.buttons.items()}
        self.group = QButtonGroup(self)
        row = QHBoxLayout()
        for key, button in self.buttons.items():
            button.setCheckable(True)
            button.setStyleSheet(CHOICE_STYLE)
            font = button.font()
            font.setPointSize(font.pointSize() + 3)
            button.setFont(font)
            button.clicked.connect(lambda _, choice=key: self.chosen.emit(choice))
            self.group.addButton(button)
            row.addWidget(button)
        row.addStretch()
        self.expected = "yes"
        self.comment = GrowingEdit(tr("Comment, needed as the reason when skipping"))
        self.comment.textChanged.connect(self.edited)
        self.hint = QLabel()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 8)
        layout.setSpacing(12)
        layout.addStretch(1)
        layout.addWidget(self.question)
        layout.addWidget(self.text)
        layout.addSpacing(8)
        layout.addLayout(row)
        layout.addWidget(self.comment)
        layout.addWidget(self.hint)
        layout.addStretch(2)

    @property
    def choice(self) -> str:
        return next((key for key, b in self.buttons.items() if b.isChecked()), "")

    @property
    def comment_text(self) -> str:
        return self.comment.toPlainText().strip()

    def ready(self) -> bool:
        return self.choice in ("yes", "no") or (self.choice == "skip" and bool(self.comment_text))

    def show_step(self, step: PlanStep, answer: str, comment: str) -> None:
        self.question.setText(step.title)
        self.expected = step.expected
        self.text.setText(step.text)
        self.text.setVisible(bool(step.text))
        self.group.setExclusive(False)
        for key, button in self.buttons.items():
            button.setChecked(key == answer)
        self.group.setExclusive(True)
        self.comment.blockSignals(True)
        self.comment.setPlainText(comment)
        self.comment.blockSignals(False)
        self.show_hint()
        self.setFocus()

    def show_hint(self) -> None:
        """Says before moving on what the answer means for the record."""
        if self.choice == "skip":
            text = "" if self.comment_text else tr("Please give the reason this point is dropped.")
        elif self.choice:
            text = (tr("Counts as passed.") if self.choice == self.expected
                    else tr("Counts as failed. A comment tells later what was noticed."))
        else:
            text = ""
        self.hint.setText(text)

    def select(self, choice: str) -> None:
        self.buttons[choice].setChecked(True)
        self.show_hint()

    def keyPressEvent(self, event) -> None:
        if event.key() in self.keys:
            self.buttons[self.keys[event.key()]].click()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.next_requested.emit()
        else:
            super().keyPressEvent(event)


class NotePage(QWidget):
    """Something to read before going on."""

    def __init__(self):
        super().__init__()
        self.title = _big_label(5)
        self.title.setStyleSheet("font-weight: bold;")
        self.text = _big_label(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 16, 24, 8)
        layout.addStretch(1)
        layout.addWidget(self.title)
        layout.addWidget(self.text)
        layout.addStretch(2)

    def show_step(self, step: PlanStep) -> None:
        self.title.setText(step.title)
        self.text.setText(step.text)


class ReasonOverlay(Overlay):
    """Why a measurement is left out. The reason goes into the report."""

    def __init__(self, parent=None, title: str = ""):
        super().__init__(title or tr("Skip step"), parent)
        self.ok_button.setText(tr("Skip"))
        self.reason = GrowingEdit(tr("Reason, it appears in the report"))
        self.reason.textChanged.connect(self._update)
        self.body.addWidget(self.reason)
        self._update()

    def first_field(self):
        return self.reason

    def _update(self) -> None:
        self.ok_button.setEnabled(bool(self.reason.toPlainText().strip()))
