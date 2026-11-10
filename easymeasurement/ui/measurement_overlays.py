# EasyMeasurement - easymeasurement/ui/measurement_overlays.py
# Entering a measurement by hand, and the clock question before an import.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import (
    QDateTimeEdit,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
)

from ..l10n import N_, tr
from ..model import FUNCTION_LABELS, Quantity, ResultValue, Verdict
from .common import function_short
from .growing_edit import GrowingEdit
from .overlay import Overlay
from .value_rows import QuietCombo, verdict_combo


class ImportOverlay(Overlay):
    """IZYTRON stored the instrument's time. Only the operator knows how far off it was."""

    def __init__(self, parent=None):
        super().__init__(tr("Import from IZYTRON"), parent, width=460)
        self.ok_button.setText(tr("Import"))
        self.offset = QSpinBox()
        self.offset.setRange(-86400, 86400)
        self.offset.setSuffix(" s")
        note = QLabel(tr(
            "If the instrument's clock was wrong back then: by how many seconds ahead (+)"
            " or behind (−)? With a correct clock this stays 0."
        ))
        note.setWordWrap(True)
        form = QFormLayout()
        form.addRow(tr("Clock offset"), self.offset)
        self.body.addWidget(note)
        self.body.addLayout(form)

    def first_field(self):
        return self.offset


class MeasurementOverlay(Overlay):
    """A measurement typed in. It may hold any number of values, even none."""

    HEADERS = (N_("Designation"), N_("Value"), N_("Lower limit"), N_("Upper limit"))

    def __init__(self, parent=None):
        super().__init__(tr("Measurement by hand"), parent, width=640)
        self.ok_button.setText(tr("Add"))
        self._named = ""
        self.function = QuietCombo()
        for key, label in FUNCTION_LABELS.items():
            self.function.addItem(label, key)
        self.function.setCurrentIndex(self.function.findData("other"))
        self.function.currentIndexChanged.connect(self._name_first_value)
        self.moment = QDateTimeEdit(QDateTime.currentDateTime())
        self.moment.setDisplayFormat("dd.MM.yyyy HH:mm:ss")
        self.moment.setCalendarPopup(True)
        self.location = QLineEdit(placeholderText=tr("Where it was measured"))
        self.comment = GrowingEdit(tr("Remark on the measurement"))
        self.verdict = verdict_combo(Verdict.NOT_EVALUATED.value)
        self.table = QTableWidget(1, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels([tr(header) for header in self.HEADERS])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        self.table.setMinimumHeight(140)
        add = QPushButton(tr("Add reading"))
        remove = QPushButton(tr("Remove reading"))
        add.clicked.connect(self._add_row)
        remove.clicked.connect(lambda: self.table.removeRow(self.table.currentRow()))
        form = QFormLayout()
        form.addRow(tr("Designation"), self.function)
        form.addRow(tr("Time"), self.moment)
        form.addRow(tr("Measuring location"), self.location)
        form.addRow(tr("Verdict"), self.verdict)
        form.addRow(tr("Remark"), self.comment)
        row = QHBoxLayout()
        row.addWidget(add)
        row.addWidget(remove)
        row.addStretch()
        self.body.addLayout(form)
        self.body.addWidget(self.table, 1)
        self.body.addLayout(row)

    def first_field(self):
        return self.function

    def _name_first_value(self) -> None:
        """The first value is usually the function's own quantity, such as RLO."""
        item = self.table.item(0, 0) if self.table.rowCount() else None
        if item is None or not item.text() or item.text() == self._named:
            self._named = function_short(self.function.currentData())
            self.table.setItem(0, 0, QTableWidgetItem(self._named))

    def _add_row(self) -> None:
        self.table.insertRow(self.table.rowCount())
        self.table.setCurrentCell(self.table.rowCount() - 1, 0)
        self.table.setFocus()

    def _cell(self, row: int, column: int) -> str:
        item = self.table.item(row, column)
        return item.text().strip() if item else ""

    def values(self) -> list[ResultValue]:
        values = []
        for row in range(self.table.rowCount()):
            label, raw = self._cell(row, 0), self._cell(row, 1)
            if not raw:
                continue
            label = label or tr("Value {number}", number=row + 1)
            values.append(ResultValue(
                key=label.casefold(), label=label, quantity=Quantity.parse(raw),
                verdict=Verdict.NOT_EVALUATED,
                lower_limit=self._cell(row, 2), upper_limit=self._cell(row, 3),
            ))
        return values

    def taken_at(self) -> datetime:
        return self.moment.dateTime().toPython()
