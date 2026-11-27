# OkeyDocu - okeydocu/ui/guide_starter.py
# Choosing the next measurement to be guided through, while measuring without a plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Offered are the measurements the instrument's driver has a guide for, followed by those of
the instruments booked beside it, each kept with the slot of its instrument. The first of a
kind in a campaign is guided through all stations; once one is there, a repeat passes by what
stays as it was."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QSizePolicy, QWidget

from ..devices import driver_info
from ..l10n import N_, tr
from .board import UNIT
from .button_width import widest
from .dial_icons import BADGE, dial_icon

LEAST = 16  # characters of a name the choice keeps in view when room is short
FIRST, REPEAT = N_("Guided measurement …"), N_("Guided repeat …")
SLOT = Qt.ItemDataRole.UserRole + 1  # the booked instrument of a guide, 0 the campaign's own

class GuideStarter(QWidget):
    requested = Signal(str)  # the function to be guided through

    def __init__(self, parent=None):
        super().__init__(parent)
        self.info = None
        self.beside: tuple[tuple[int, str], ...] = ()  # slot and driver of instruments beside
        self.measured: set[str] = set()
        self.choice = QComboBox()
        self.choice.setIconSize(BADGE)
        # The choice fills the room it gets and gives way to a short name; its list stays
        # as wide as the longest.
        self.choice.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.choice.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.choice.setMinimumWidth(BADGE.width() + 40
                                    + self.choice.fontMetrics().averageCharWidth() * LEAST)
        self.choice.currentIndexChanged.connect(lambda _: self._label())
        self.button = QPushButton()
        self.button.clicked.connect(self._request)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(2 * UNIT)
        row.addWidget(self.choice)
        row.addWidget(self.button)
        self.hide()

    def show_campaign(self, driver: str, measured: set[str],
                      beside: tuple[tuple[int, str], ...] = ()) -> None:
        """`driver` is the key of the instrument measuring, empty without one; `measured` the
        functions the campaign has readings of; `beside` slot and driver of each instrument
        booked beside it."""
        info = driver_info(driver) if driver else None
        self.measured = measured
        if info is not self.info or beside != self.beside:
            self.info, self.beside = info, beside
            kept = self.choice.currentData()
            self.choice.blockSignals(True)
            self.choice.clear()
            sources = ((0, info),) if info is not None else ()
            for slot, info_of in sources + tuple((slot, driver_info(key)) for slot, key in beside):
                for function in info_of.guided if info_of is not None else ():
                    if self.choice.findData(function) >= 0:
                        continue  # one guide per function, from the first instrument with it
                    guide = info_of.guide(function)
                    self.choice.addItem(dial_icon(info_of.panel, guide.selector),
                                        tr(guide.title), function)
                    self.choice.setItemData(self.choice.count() - 1, slot, SLOT)
            self.choice.view().setMinimumWidth(self.choice.sizeHint().width())
            self.choice.setCurrentIndex(max(self.choice.findData(kept), 0))
            self.choice.blockSignals(False)
        self.setVisible(self.choice.count() > 0)
        self._label()

    def follow(self, position) -> None:
        """The switch stands on a position one of the guides serves: the guide that leads to
        this very position is chosen, else the first whose function it produces."""
        functions = [self.choice.itemData(index) for index in range(self.choice.count())
                     if not self.choice.itemData(index, SLOT)]
        own = [function for function in functions
               if self.info.guide(function).selector == position.value]
        served = own or [function for function in functions if function in position.functions]
        if served:
            self.choice.setCurrentIndex(self.choice.findData(served[0]))

    def slot_of(self, function: str) -> int:
        """The slot of the instrument whose guide is offered for `function`."""
        index = self.choice.findData(function)
        return (self.choice.itemData(index, SLOT) or 0) if index >= 0 else 0

    def guide_of(self, function: str):
        slot = self.slot_of(function)
        key = dict(self.beside).get(slot) if slot else None
        info = driver_info(key) if key else self.info
        return info.guide(function) if info is not None else None

    def is_first(self, function: str) -> bool:
        guide = self.guide_of(function)
        return guide is not None and not any(guide.ended_by(f) for f in self.measured)

    def _label(self) -> None:
        function = self.choice.currentData()
        first = function is not None and self.is_first(function)
        # Wide enough for either text, so the choice beside it keeps its width.
        self.button.setFixedWidth(widest(self.button, (tr(FIRST), tr(REPEAT))))
        self.button.setText(tr(FIRST) if first else tr(REPEAT))
        self.button.setToolTip(tr("Leads through the first measurement of this kind step by"
                                  " step.") if first else
                               tr("Leads through the next measurement of this kind, passing"
                                  " by what stays as it was."))

    def _request(self) -> None:
        if self.choice.currentData() is not None:
            self.requested.emit(self.choice.currentData())
