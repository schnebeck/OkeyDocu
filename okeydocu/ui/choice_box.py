# OkeyDocu - okeydocu/ui/choice_box.py
# A field that offers values to choose from and still takes any other text.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The list of a choice box always starts with two entries of its own: one that empties the
field and one that clears it for a text of one's own. Neither is a value: choosing one leaves
the field empty, the second with the cursor in it. Typed text is neither completed to an
offered value nor added to the list.

Offered from a choice list, each value tells in its tooltip what sets it apart from the others,
with its help, curve, picture and suited measurements; so does the field for the value it holds,
and for the list as a whole while it is empty. F1 in the field sets all values of the list side
by side, the one held in bold."""
from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QEvent, QObject, QPoint, Qt
from PySide6.QtWidgets import QComboBox, QLineEdit

from ..l10n import N_, tr
from ..store.choice_lists import ChoiceList
from .choice_tips import Context, choice_text, compare_tip, held_value, list_tip, text_tip
from .rich_tip import Tip, install_tip, widget_tip

EMPTY, OWN = "empty", "own"
LABELS = {EMPTY: N_("(empty)"), OWN: N_("Own text …")}
VALUE = Qt.ItemDataRole.UserRole + 1  # the value as the list holds it


class ChoiceBox(QComboBox):
    def __init__(self, offered: ChoiceList | tuple[str, ...], value: str = "",
                 context: Context | None = None):
        super().__init__(editable=True)
        self.list = offered if isinstance(offered, ChoiceList) else ChoiceList("", "")
        self.context = context
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(None)
        italic = self.font()
        italic.setItalic(True)
        for kind, label in LABELS.items():
            self.addItem(tr(label), kind)
            self.setItemData(self.count() - 1, italic, Qt.ItemDataRole.FontRole)
        self.insertSeparator(len(LABELS))
        values = self.list.offered if isinstance(offered, ChoiceList) else offered
        for choice in values:
            self.addItem(choice_text(choice))
            self.setItemData(self.count() - 1, choice, VALUE)
        self.lineEdit().setPlaceholderText(tr("choose or type"))
        self.setEditText(value)
        self.activated.connect(self._chosen)
        install_tip(self.lineEdit(), lambda _: self.tip(self.currentText()))
        install_tip(self, lambda _: self.tip(self.currentText()))
        install_tip(self.view().viewport(), self._row_tip)
        self.lineEdit().installEventFilter(_CompareKey(self))

    def tip(self, text: str) -> Tip | None:
        if not text.strip():
            found = list_tip(self.list)
        else:
            found = text_tip(self.list, text, self.context() if self.context else None)
        if found is None or not self.list.telling():
            return found
        return replace(found, hint=tr("F1 compares all values of the list."))

    def compare(self) -> None:
        tip = compare_tip(self.list, held_value(self.list, self.currentText()))
        if tip is not None:
            widget_tip(tip, self)

    def _row_tip(self, where: QPoint) -> Tip | None:
        value = self.view().indexAt(where).data(VALUE)
        return self.tip(value) if value else None

    def _chosen(self, index: int) -> None:
        kind = self.itemData(index)
        if kind not in LABELS:
            return
        self.setEditText("")
        if kind == OWN:
            self.lineEdit().setFocus()


class _CompareKey(QObject):
    """F1 in the field compares the values; the field takes the key before any shortcut of the
    window does."""

    def __init__(self, box: ChoiceBox):
        super().__init__(box)
        self.box = box

    def eventFilter(self, watched, event) -> bool:  # noqa: N802 - Qt's name
        if event.type() not in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
            return False
        if event.key() != Qt.Key.Key_F1 or not self.box.list.values:
            return False
        if event.type() == QEvent.Type.ShortcutOverride:
            event.accept()
            return True
        self.box.compare()
        return True


def feature_field(feature, value: str, lists: dict[str, ChoiceList] | None = None,
                  context: Context | None = None):
    """A feature offering a list is a choice box that still takes any other value."""
    offered = (lists or {}).get(feature.choice_list or "")
    if offered is None or not offered.values:
        return QLineEdit(value)
    return ChoiceBox(offered, value, context)


def field_text(field) -> str:
    return field.currentText() if isinstance(field, QComboBox) else field.text()
