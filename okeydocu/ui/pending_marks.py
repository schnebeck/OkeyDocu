# OkeyDocu - okeydocu/ui/pending_marks.py
# Input fields changed but not yet applied stand out in light yellow until they are applied.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""`watch` notes what every input field below a widget holds; a field that then differs gets
the property `pending`, which `PENDING_RULE` colours, and loses it when its value returns.
`watch` again, after applying, takes the fields as they are now. The rule is added to the
style sheet of the watched widget; a field with a style sheet of its own, such as one marking
a missing value, keeps that colour."""

from __future__ import annotations

from PySide6.QtCore import QObject
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QLineEdit,
    QPlainTextEdit,
    QTextEdit,
    QWidget,
)

PENDING_RULE = '*[pending="true"] { background-color: #fff7c2; }'
WATCHED = "pendingWatched"


def _read(widget: QWidget):
    """What a field holds, or None for a widget that is no input field of its own."""
    if isinstance(widget, QLineEdit):
        inner = isinstance(widget.parent(), (QComboBox, QAbstractSpinBox))
        return None if inner or widget.isReadOnly() else widget.text()
    if isinstance(widget, QComboBox):
        return widget.currentText()
    if isinstance(widget, (QPlainTextEdit, QTextEdit)):
        return None if widget.isReadOnly() else widget.toPlainText()
    if isinstance(widget, QDateTimeEdit):
        return widget.dateTime()
    if isinstance(widget, QAbstractSpinBox):
        return widget.text()
    if isinstance(widget, QCheckBox):
        return widget.isChecked()
    return None


def _changes(widget: QWidget):
    if isinstance(widget, QComboBox):
        return widget.currentTextChanged
    if isinstance(widget, QDateTimeEdit):
        return widget.dateTimeChanged
    if isinstance(widget, QCheckBox):
        return widget.toggled
    return widget.textChanged


class PendingMarks(QObject):
    def __init__(self, root: QWidget):
        super().__init__(root)
        self.root = root
        root.setStyleSheet(f"{root.styleSheet()} {PENDING_RULE}".strip())
        self.start: dict[QWidget, object] = {}

    def watch(self) -> None:
        """Takes every field as it is now; none is marked."""
        self.start.clear()
        for widget in self.root.findChildren(QWidget):
            value = _read(widget)
            if value is None:
                continue
            self.start[widget] = value
            if not widget.property(WATCHED):
                _changes(widget).connect(lambda *_, field=widget: self._check(field))
                widget.setProperty(WATCHED, True)
            self._mark(widget, False)

    def pending(self) -> list[QWidget]:
        return [widget for widget in self.start if widget.property("pending")]

    def _check(self, widget: QWidget) -> None:
        if widget in self.start:
            self._mark(widget, _read(widget) != self.start[widget])

    @staticmethod
    def _mark(widget: QWidget, on: bool) -> None:
        if bool(widget.property("pending")) == on:
            return
        widget.setProperty("pending", on)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()
