# OkeyDocu - okeydocu/ui/station_bar.py
# The row of stations above a guided measurement: done, now, still to come.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..l10n import tr

DONE = "background:#2e8b57;color:white"
NOW = "background:#ff9f1c;color:#1f2933;font-weight:bold"
LATER = "background:#d5dadf;color:#555"


class StationBar(QWidget):
    def __init__(self, names: tuple[str, ...], parent=None):
        super().__init__(parent)
        self.names = names
        self.chips = [QLabel() for _ in names]
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        for chip in self.chips:
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.addWidget(chip)

    def show_station(self, current: int, count: int) -> None:
        """Only the first `count` stations are part of this run."""
        for index, (chip, name) in enumerate(zip(self.chips, self.names)):
            chip.setVisible(index < count)
            state = DONE if index < current else NOW if index == current else LATER
            mark = "✓" if index < current else str(index + 1)
            chip.setText(f"{mark}  {tr(name)}")
            chip.setStyleSheet(state + ";border-radius:12px;padding:6px 10px")
