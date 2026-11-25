# OkeyDocu - okeydocu/ui/rcd_where.py
# The question of the first station where the RCD of a measurement stands.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A measurement that needs an RCD asks this where none stands at or above the element chosen:
the RCD is an element of the installation, to be made on the way, or it stands in front, in
the building installation, and is stated at the installation."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QRadioButton, QVBoxLayout, QWidget

from ..l10n import tr


class RcdWhere(QWidget):
    chosen = Signal(bool)  # picked by the tester: the RCD stands in front

    def __init__(self, parent=None):
        super().__init__(parent)
        self.quiet = False  # the answer is being shown, not given
        self.inside = QRadioButton(tr("An element of this installation"))
        self.in_front = QRadioButton(tr("In front of it, in the building installation"))
        self.in_front.toggled.connect(self._picked)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)  # apart from the details that follow
        layout.addWidget(QLabel(f"<b>{tr('Where is the RCD?')}</b>"))
        layout.addWidget(self.inside)
        layout.addWidget(self.in_front)

    def show_answer(self, in_front: bool) -> None:
        self.quiet = True
        (self.in_front if in_front else self.inside).setChecked(True)
        self.quiet = False

    def _picked(self, in_front: bool) -> None:
        if not self.quiet:
            self.chosen.emit(in_front)
