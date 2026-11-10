# EasyMeasurement - easymeasurement/ui/language_choice.py
# Choosing the language the program speaks.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QComboBox, QFormLayout

from ..l10n import SOURCE, N_, available, speaking, tr
from .overlay import Overlay
from .report_signing import settings

KEY = "language"
SYSTEM = ""  # stored for "as the system": the system decides at every start
NEXT_START = N_("Applies from the next start.")


def system_language() -> str:
    code = QLocale.system().name().split("_")[0]
    return code if code in available(program=True) else SOURCE


def chosen_language() -> str:
    stored = settings().value(KEY, SYSTEM)
    return stored if stored in available(program=True) else system_language()


class LanguageOverlay(Overlay):
    """Every language is listed in its own name, so it can be found without reading the
    current one. The note under the choice speaks the language chosen there."""

    def __init__(self, parent=None):
        super().__init__(tr("Language"), parent)
        self.choice = QComboBox()
        self.choice.addItem(tr("As the system ({language})",
                               language=available()[system_language()]), SYSTEM)
        for code, name in available(program=True).items():
            self.choice.addItem(name, code)
        stored = settings().value(KEY, SYSTEM)
        self.choice.setCurrentIndex(max(0, self.choice.findData(stored)))
        self.choice.currentIndexChanged.connect(lambda _: self._explain())
        form = QFormLayout()
        form.addRow(tr("Program language"), self.choice)
        self.body.addLayout(form)
        self._explain()

    def _explain(self) -> None:
        with speaking(self.choice.currentData() or system_language()):
            self.hint.setText(tr(NEXT_START))

    def accept(self) -> None:
        settings().setValue(KEY, self.choice.currentData())
        super().accept()
