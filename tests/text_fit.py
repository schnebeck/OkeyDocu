# EasyMeasurement - tests/text_fit.py
# Finds texts that do not fit the widget showing them, as a person would see them cut off.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextDocument
from PySide6.QtWidgets import (
    QAbstractButton,
    QApplication,
    QComboBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QStyle,
    QWidget,
)

SLACK_PX = 1  # rounding of text metrics
_MARKUP = re.compile(r"<[a-zA-Z/][^>]*>|&[a-z]+;")


def _label_need(label: QLabel) -> int | None:
    """Width a one-line label needs; None for those that wrap, show pictures or elide."""
    text = label.text()
    if not text or label.wordWrap() or label.pixmap() and not label.pixmap().isNull():
        return None
    if label.textFormat() == Qt.TextFormat.RichText or _MARKUP.search(text):
        document = QTextDocument()
        document.setDefaultFont(label.font())
        document.setHtml(text)
        document.setDocumentMargin(0)
        return int(document.idealWidth())
    lines = text.splitlines() or [text]
    return max(label.fontMetrics().horizontalAdvance(line) for line in lines)


BUTTON_PADDING_PX = 12  # frame and margins of a push button in the usual styles


def _button_need(button: QAbstractButton) -> int | None:
    """Width of the text and icon; a style's minimum width for buttons does not count."""
    text = button.text().replace("&", "")
    if not text:
        return None
    icon = button.iconSize().width() + 4 if not button.icon().isNull() else 0
    return button.fontMetrics().horizontalAdvance(text) + icon + BUTTON_PADDING_PX


COMBO_EXTRA_PX = 30  # frame and arrow of a combo box
EDIT_EXTRA_PX = 8  # frame and text margins of a line edit


def _combo_need(box: QComboBox) -> int | None:
    """The chosen entry; an editable box shows what is typed, a list may scroll."""
    text = box.currentText()
    if not text or box.isEditable():
        return None
    icon = box.iconSize().width() + 4 if not box.itemIcon(box.currentIndex()).isNull() else 0
    return box.fontMetrics().horizontalAdvance(text) + icon + COMBO_EXTRA_PX


def _placeholder_need(edit: QLineEdit) -> int | None:
    """The hint of an empty field, which says what belongs in it."""
    if edit.text() or not edit.placeholderText():
        return None
    return edit.fontMetrics().horizontalAdvance(edit.placeholderText()) + EDIT_EXTRA_PX


def _visible_width(widget: QWidget) -> int:
    """How much of the widget its parents leave in view: a label wider than the button it
    sits on is cut at the button's edge."""
    shown = widget.rect()
    child, parent = widget, widget.parentWidget()
    offset = widget.pos()
    while parent is not None:
        shown = shown.intersected(parent.rect().translated(-offset))
        child, parent = parent, parent.parentWidget()
        offset += child.pos()
    return max(0, shown.width())


def _shown(widget: QWidget) -> str:
    if isinstance(widget, QComboBox):
        return widget.currentText()
    if isinstance(widget, QLineEdit):
        return widget.placeholderText()
    return widget.text()


SORT_ARROW_PX = 16


def header_cuts(header: QHeaderView) -> list[str]:
    """Column titles narrower than their text, as long as the column can be seen at all."""
    model, found = header.model(), []
    if model is None or not header.isVisible():
        return found
    metrics = header.fontMetrics()
    margins = 2 * header.style().pixelMetric(QStyle.PixelMetric.PM_HeaderMargin)
    for section in range(header.count()):
        if header.isSectionHidden(section):
            continue
        text = str(model.headerData(section, header.orientation()) or "")
        width = header.sectionSize(section)
        sorted_by = header.isSortIndicatorShown() and header.sortIndicatorSection() == section
        need = metrics.horizontalAdvance(text) + margins + (SORT_ARROW_PX if sorted_by else 0)
        if text and need > width + SLACK_PX:
            found.append(f"column {text!r}: needs {need}, has {width}")
    return found


def cut_texts(root: QWidget) -> list[str]:
    """Visible labels and buttons whose text is wider than the room they have."""
    QApplication.processEvents()
    found = []
    for widget in [root, *root.findChildren(QWidget)]:
        if not widget.isVisibleTo(root) or widget.width() <= 1:
            continue
        if isinstance(widget, QHeaderView) and widget.orientation() == Qt.Orientation.Horizontal:
            found += header_cuts(widget)
            continue
        if isinstance(widget, QLabel):
            need = _label_need(widget)
            room = widget.contentsRect().width() - 2 * widget.margin()
        elif isinstance(widget, QAbstractButton):
            need = _button_need(widget)
            room = widget.width()
        elif isinstance(widget, QComboBox):
            need = _combo_need(widget)
            room = widget.width()
        elif isinstance(widget, QLineEdit):
            need = _placeholder_need(widget)
            room = widget.width()
        else:
            continue
        if need is None:
            continue
        visible = _visible_width(widget)
        if visible == 0:  # scrolled out of view
            continue
        room = min(room, visible)
        if need > room + SLACK_PX:
            text = _shown(widget).replace("\n", " ")
            found.append(f"{type(widget).__name__} {text[:60]!r}: needs {need}, has {room}")
    return found
