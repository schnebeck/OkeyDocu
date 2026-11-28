# OkeyDocu - okeydocu/ui/instrument_adding.py
# The choice of a kind of instrument to add, however many kinds the program supports.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""One entry per kind that is made known to the program once: paired over Bluetooth or
enrolled as a sensor. Typing in the field narrows the entries to those containing what is
typed, so a long list is searched rather than scrolled."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QCompleter, QHBoxLayout, QLabel, QPushButton, QWidget

from ..devices import available_drivers
from ..l10n import N_, tr

PAIR, ENROL = N_("{instrument} – pair over Bluetooth"), N_("{instrument} – enrol")


class InstrumentAdding(QWidget):
    chosen = Signal(object)  # the DriverInfo of the kind to add

    def __init__(self, parent=None):
        super().__init__(parent)
        self.kinds = QComboBox()
        self.kinds.setEditable(True)
        self.kinds.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.kinds.lineEdit().setPlaceholderText(tr("Kind of instrument"))
        for info in sorted(available_drivers(), key=lambda info: tr(info.label).lower()):
            if info.pairing is not None or info.enrolment is not None:
                way = PAIR if info.pairing is not None else ENROL
                self.kinds.addItem(tr(way, instrument=tr(info.label)), info)
        completer = QCompleter(self.kinds.model(), self.kinds)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.kinds.setCompleter(completer)
        self.kinds.setCurrentIndex(-1)
        self.add_button = QPushButton(tr("Add …"))
        self.add_button.clicked.connect(self._add)
        self.kinds.currentIndexChanged.connect(lambda _: self._update())
        self.kinds.editTextChanged.connect(lambda _: self._update())
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(QLabel(tr("Add instrument")))
        row.addWidget(self.kinds, 1)
        row.addWidget(self.add_button)
        self._update()

    def _info(self):
        """The kind whose entry the field shows exactly; none while typing a part of it."""
        index = self.kinds.findText(self.kinds.currentText(), Qt.MatchFlag.MatchExactly)
        return self.kinds.itemData(index) if index >= 0 else None

    def _update(self) -> None:
        self.add_button.setEnabled(self._info() is not None)

    def choose(self, key: str) -> None:
        index = next((i for i in range(self.kinds.count()) if self.kinds.itemData(i).key == key),
                     -1)
        self.kinds.setCurrentIndex(index)

    def _add(self) -> None:
        info = self._info()
        if info is not None:
            self.chosen.emit(info)
