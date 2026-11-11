# EasyMeasurement - easymeasurement/ui/instrument_log.py
# An instrument's log: its tests and the campaigns it measured in, read from the records only.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
)

from ..devices.instrument_check import Check
from ..l10n import N_, day, moment, signed_seconds, tr
from .common import AppContext
from .instrument_test import MARKS, run_text
from .overlay import Overlay

COLUMNS = (N_("Time"), N_("Entry"), N_("Firmware"), N_("Calibrated"), N_("Due"), N_("Clock"))
EMPTY = N_("No instrument tested or used in a campaign yet.")


def _day(text: str) -> str:
    return day(date.fromisoformat(text)) if text else ""


def _line(entry) -> list[str]:
    mark = "" if entry.ready is None else ("✓ " if entry.ready else "✗ ")
    clock = "" if entry.clock_offset_s is None else f"{signed_seconds(entry.clock_offset_s)} s"
    return [moment(datetime.fromisoformat(entry.moment)), mark + entry.title,
            entry.firmware, _day(entry.calibrated_on), _day(entry.recalibration_due), clock]


class InstrumentLogOverlay(Overlay):
    """Opens without the instrument: nothing here needs a connection."""

    def __init__(self, app: AppContext, parent=None):
        super().__init__(tr("Instrument log"), parent, 860)
        self.app = app
        self.instrument = QComboBox()
        for serial, model in app.service.known_instruments():
            self.instrument.addItem(tr("{model}, serial number {serial}", model=model,
                                       serial=serial), serial)
        self.instrument.currentIndexChanged.connect(lambda _: self._fill())
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr(column) for column in COLUMNS])
        self.tree.setRootIsDecorated(True)
        self.tree.setMinimumHeight(320)
        self.tree.setToolTip(tr("Click ▸ to show the single checks of a test"))
        self.copy_button = QPushButton(tr("Copy as text"))
        self.copy_button.clicked.connect(self._copy)
        top = QHBoxLayout()
        top.addWidget(QLabel(tr("Instrument")))
        top.addWidget(self.instrument, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(self.copy_button)
        self.body.addLayout(top)
        self.body.addWidget(self.tree, 1)
        self.body.addLayout(row)
        self.ok_button.setText(tr("Back"))
        self.cancel_button.hide()
        self.hint.setText("" if self.instrument.count() else tr(EMPTY))
        self._fill()

    def _fill(self) -> None:
        self.tree.clear()
        serial = self.instrument.currentData()
        self.entries = self.app.service.instrument_history(serial) if serial else []
        for entry in self.entries:
            item = QTreeWidgetItem(_line(entry))
            self.tree.addTopLevelItem(item)
            for check in entry.checks:
                child = QTreeWidgetItem([f"{MARKS[check['state']]}  {check['title']}:"
                                         f" {check['detail']}"])
                item.addChild(child)
                child.setFirstColumnSpanned(True)  # a sentence, not values for the columns
        for column in range(len(COLUMNS)):
            self.tree.resizeColumnToContents(column)
        self.copy_button.setEnabled(bool(self.entries))

    def _copy(self) -> None:
        lines = [self.instrument.currentText(), ""]
        for entry in self.entries:
            lines.append("  ".join(part for part in _line(entry) if part))
            if entry.checks:
                checks = [Check(**check) for check in entry.checks]
                lines += ["    " + text for text in run_text(checks, entry.ready).splitlines()
                          if text]
        QGuiApplication.clipboard().setText("\n".join(lines))
