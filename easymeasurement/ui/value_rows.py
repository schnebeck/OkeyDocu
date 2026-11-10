# EasyMeasurement - easymeasurement/ui/value_rows.py
# The values of one measurement, with label, limits and verdict open to correction.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QAbstractItemView, QComboBox, QHeaderView, QTableWidgetItem

from ..l10n import N_, tr
from ..model import Verdict, check_text
from ..reporting.context import VERDICT_TEXT
from .common import make_table, verdict_item

HEADERS = (N_("Reading"), N_("Value"), N_("Low"), N_("High"), N_("Verd."))
LABEL, VALUE, LOWER, UPPER, VERDICT = range(len(HEADERS))
_TEXT_COLUMNS = {LABEL: "label", LOWER: "lower_limit", UPPER: "upper_limit"}
_FAILED_STYLE = "QComboBox { color: #c0392b; font-weight: bold; }"
SHOWN_ROWS = 8
FINAL_TIP = N_("Reading, unit and time are fixed.")


class QuietCombo(QComboBox):
    """Turns with the mouse wheel only once clicked, so scrolling past it changes nothing."""

    def __init__(self):
        super().__init__()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        # Long names must not widen the panel it stands in; the open list shows them whole.
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(10)

    def wheelEvent(self, event) -> None:
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


# The usual marks of a test record, so a verdict fits a narrow column.
SHORT_VERDICT = {Verdict.NOT_EVALUATED: "–", Verdict.PASSED: N_("pass"), Verdict.FAILED: N_("fail")}


def verdict_combo(current: str, short: bool = False) -> QuietCombo:
    box = QuietCombo()
    if short:
        box.setMinimumContentsLength(5)
    for verdict in (Verdict.NOT_EVALUATED, Verdict.PASSED, Verdict.FAILED):
        box.addItem(tr(SHORT_VERDICT[verdict]) if short else tr(VERDICT_TEXT[verdict]), verdict.value)
        box.setItemData(box.count() - 1, tr(VERDICT_TEXT[verdict]), Qt.ItemDataRole.ToolTipRole)
    box.setCurrentIndex(max(0, box.findData(current)))
    mark_failed(box)
    box.currentIndexChanged.connect(lambda: mark_failed(box))
    return box


def mark_failed(box: QComboBox) -> None:
    box.setStyleSheet(_FAILED_STYLE if box.currentData() == Verdict.FAILED.value else "")


def _value_text(value) -> str:
    text = check_text(value["raw"])
    if not value["setpoint"]:
        return text
    return tr("{value} (target {setpoint})", value=text, setpoint=check_text(value["setpoint"]))


class ValueRows(QObject):
    """A table of values. Edits stay in the table until `changes()` hands them on."""

    edited = Signal()

    def __init__(self):
        super().__init__()
        self.table = make_table([tr(header) for header in HEADERS], stretch=LABEL)
        # Narrow as the panel is, the columns share its width instead of scrolling sideways.
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.table.horizontalHeader().setMinimumSectionSize(30)
        self.rows: list = []
        self._filling = False
        self.table.itemChanged.connect(self._item_changed)

    def fill(self, values: list, editable: bool) -> None:
        self._filling = True
        self.rows = list(values)
        table = self.table
        for index in range(table.rowCount()):
            self._drop_box(index)
        table.setRowCount(len(self.rows))
        table.setVisible(bool(self.rows))
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            if editable else QAbstractItemView.EditTrigger.NoEditTriggers
        )
        for index, value in enumerate(self.rows):
            open_here = editable and value["kind"] != "photo"
            for column, field in _TEXT_COLUMNS.items():
                item = QTableWidgetItem(value[field] or "")
                if not open_here:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                table.setItem(index, column, item)
            final = QTableWidgetItem(_value_text(value))
            final.setFlags(final.flags() & ~Qt.ItemFlag.ItemIsEditable)
            final.setToolTip(tr(FINAL_TIP))
            table.setItem(index, VALUE, final)
            self._drop_box(index)
            if open_here:
                box = verdict_combo(value["verdict"], short=True)
                box.currentIndexChanged.connect(lambda: self.edited.emit())
                table.setItem(index, VERDICT, QTableWidgetItem())
                table.setCellWidget(index, VERDICT, box)
            else:
                item = verdict_item(value["verdict"])
                item.setToolTip(item.text())
                item.setText(tr(SHORT_VERDICT[Verdict(value["verdict"])]))
                table.setItem(index, VERDICT, item)
        self._filling = False
        self._size_verdicts()
        self._fit()

    def _size_verdicts(self) -> None:
        """A choice box is not measured with the cells, so its column is set to fit it."""
        header = self.table.horizontalHeader()
        boxes = [self.table.cellWidget(i, VERDICT) for i in range(self.table.rowCount())]
        boxes = [box for box in boxes if box is not None]
        if boxes:
            header.setSectionResizeMode(VERDICT, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(VERDICT, max(box.sizeHint().width() for box in boxes))
        else:
            header.setSectionResizeMode(VERDICT, QHeaderView.ResizeMode.ResizeToContents)

    def _fit(self) -> None:
        """As tall as its rows, up to `SHOWN_ROWS`; beyond that it scrolls."""
        table = self.table
        rows = min(max(table.rowCount(), 1), SHOWN_ROWS)
        table.setFixedHeight(
            table.horizontalHeader().sizeHint().height()
            + rows * table.verticalHeader().defaultSectionSize() + 2 * table.frameWidth()
        )

    def _drop_box(self, index: int) -> None:
        """Hidden at once: the table deletes it only when the event loop comes round."""
        box = self.table.cellWidget(index, VERDICT)
        if box is not None:
            box.hide()
            self.table.removeCellWidget(index, VERDICT)

    def _item_changed(self, _item) -> None:
        if not self._filling:
            self.edited.emit()

    def _current(self, index: int) -> dict[str, str]:
        fields = {
            field: self.table.item(index, column).text().strip()
            for column, field in _TEXT_COLUMNS.items()
        }
        box = self.table.cellWidget(index, VERDICT)
        if box is not None:
            fields["verdict"] = box.currentData()
        return fields

    def changes(self) -> dict[int, dict[str, str]]:
        """Only what differs from the stored value, by value id."""
        changes = {}
        for index, value in enumerate(self.rows):
            if value["kind"] == "photo":
                continue
            differs = {
                k: v for k, v in self._current(index).items() if v != (value[k] or "")
            }
            if differs:
                changes[value["id"]] = differs
        return changes

    def focus_first(self) -> None:
        if self.rows:
            self.table.setFocus()
            self.table.setCurrentCell(0, LABEL)
