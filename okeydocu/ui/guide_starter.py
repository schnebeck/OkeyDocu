# OkeyDocu - okeydocu/ui/guide_starter.py
# Choosing the next measurement to be guided through, while measuring without a plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Offered are the measurements the instrument's driver has a guide for. The first of a kind
in a campaign is guided through all stations; once one is there, a repeat passes by what stays
as it was."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QWidget

from ..devices import driver_info
from ..l10n import tr


class GuideStarter(QWidget):
    requested = Signal(str)  # the function to be guided through

    def __init__(self, parent=None):
        super().__init__(parent)
        self.info = None
        self.measured: set[str] = set()
        self.choice = QComboBox()
        self.choice.currentIndexChanged.connect(lambda _: self._label())
        self.button = QPushButton()
        self.button.clicked.connect(self._request)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.choice)
        row.addWidget(self.button)
        self.hide()

    def show_campaign(self, driver: str, measured: set[str]) -> None:
        """`driver` is the key of the instrument measuring, empty without one; `measured` the
        functions the campaign has readings of."""
        info = driver_info(driver) if driver else None
        self.measured = measured
        if info is not self.info:
            self.info = info
            kept = self.choice.currentData()
            self.choice.blockSignals(True)
            self.choice.clear()
            for function in (info.guided if info is not None else ()):
                self.choice.addItem(tr(info.guide(function).title), function)
            self.choice.setCurrentIndex(max(self.choice.findData(kept), 0))
            self.choice.blockSignals(False)
        self.setVisible(self.choice.count() > 0)
        self._label()

    def follow(self, position) -> None:
        """The switch stands on a position one of the guides serves: the guide that leads to
        this very position is chosen, else the first whose function it produces."""
        functions = [self.choice.itemData(index) for index in range(self.choice.count())]
        own = [function for function in functions
               if self.info.guide(function).selector == position.value]
        served = own or [function for function in functions if function in position.functions]
        if served:
            self.choice.setCurrentIndex(functions.index(served[0]))

    def is_first(self, function: str) -> bool:
        guide = self.info.guide(function) if self.info is not None else None
        return guide is not None and not any(guide.ended_by(f) for f in self.measured)

    def _label(self) -> None:
        function = self.choice.currentData()
        first = function is not None and self.is_first(function)
        self.button.setText(tr("Guided measurement …") if first else tr("Guided repeat …"))
        self.button.setToolTip(tr("Leads through the first measurement of this kind step by"
                                  " step.") if first else
                               tr("Leads through the next measurement of this kind, passing"
                                  " by what stays as it was."))

    def _request(self) -> None:
        if self.choice.currentData() is not None:
            self.requested.emit(self.choice.currentData())
