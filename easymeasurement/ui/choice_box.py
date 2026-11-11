# EasyMeasurement - easymeasurement/ui/choice_box.py
# A field that offers values to choose from and still takes any other text.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The list of a choice box always starts with two entries of its own: one that empties the
field and one that clears it for a text of one's own. Neither is a value: choosing one leaves
the field empty, the second with the cursor in it. Typed text is neither completed to an
offered value nor added to the list."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QLineEdit

from ..l10n import N_, tr
from ..l10n.formats import pattern

EMPTY, OWN = "empty", "own"
LABELS = {EMPTY: N_("(empty)"), OWN: N_("Own text …")}


def choice_text(choice: str) -> str:
    """A number with the decimal sign of the language, a word in the language."""
    try:
        float(choice)
    except ValueError:
        return tr(choice)
    return choice.replace(".", pattern("decimal"))


class ChoiceBox(QComboBox):
    def __init__(self, choices, value: str = ""):
        super().__init__(editable=True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setCompleter(None)
        italic = self.font()
        italic.setItalic(True)
        for kind, label in LABELS.items():
            self.addItem(tr(label), kind)
            self.setItemData(self.count() - 1, italic, Qt.ItemDataRole.FontRole)
        self.insertSeparator(len(LABELS))
        self.addItems([choice_text(choice) for choice in choices])
        self.lineEdit().setPlaceholderText(tr("choose or type"))
        self.setEditText(value)
        self.activated.connect(self._chosen)

    def _chosen(self, index: int) -> None:
        kind = self.itemData(index)
        if kind not in LABELS:
            return
        self.setEditText("")
        if kind == OWN:
            self.lineEdit().setFocus()


def feature_field(feature, value: str):
    """A feature with choices offers them and still takes any other value."""
    return ChoiceBox(feature.choices, value) if feature.choices else QLineEdit(value)


def field_text(field) -> str:
    return field.currentText() if isinstance(field, QComboBox) else field.text()
