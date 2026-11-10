# EasyMeasurement - easymeasurement/ui/language_choice.py
# Choosing the language the program speaks.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QFormLayout

from ..l10n import available, current, tr
from .overlay import Overlay
from .report_signing import settings

KEY = "language"


class LanguageOverlay(Overlay):
    """Every language is listed in its own name. The choice applies from the next start,
    because texts already shown are not looked up again."""

    def __init__(self, parent=None):
        super().__init__(tr("Language"), parent)
        self.choice = QComboBox()
        for code, name in available(program=True).items():
            self.choice.addItem(name, code)
        self.choice.setCurrentIndex(max(0, self.choice.findData(current())))
        form = QFormLayout()
        form.addRow(tr("Program language"), self.choice)
        self.body.addLayout(form)
        self.hint.setText(tr("Applies from the next start."))

    def accept(self) -> None:
        settings().setValue(KEY, self.choice.currentData())
        super().accept()
