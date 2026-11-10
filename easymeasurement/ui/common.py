# EasyMeasurement - easymeasurement/ui/common.py
# Shared UI helpers and the objects every page works with.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
import random
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from PySide6.QtCore import QEventLoop, Qt, QThread
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QMessageBox,
    QProgressDialog,
    QTableWidget,
    QTableWidgetItem,
)

from ..campaign.service import CampaignService
from ..devices import MeterDriver, create_driver
from ..devices.simulator import SimulatedMeter
from ..model import FUNCTION_LABELS, Parameter, Verdict, check_text, conductor_of
from ..reporting.archive import ReportArchive
from ..reporting.context import VERDICT_TEXT
from ..store import Database

T = TypeVar("T")

ROW_ID = Qt.ItemDataRole.UserRole
RUN_ID = Qt.ItemDataRole.UserRole + 30  # on a line standing for a whole run
MEMBERS = Qt.ItemDataRole.UserRole + 31  # the measurements such a line stands for
POINT_ID = Qt.ItemDataRole.UserRole + 32  # on a line for a point still to be taken


SIMULATED_FAILURE_RATE = 0.15


@dataclass
class DeviceSession:
    """Keeps instruments per campaign, so a simulator holds its stored readings."""

    drivers: dict[int, MeterDriver] = field(default_factory=dict)
    ports: dict[int, str] = field(default_factory=dict)

    def new_driver(self, key: str, port: str = "") -> MeterDriver:
        if key == "simulator":
            return SimulatedMeter(
                clock_skew_s=random.randint(-300, 300), failure_rate=SIMULATED_FAILURE_RATE
            )
        return create_driver(key, port=port)

    def attach(self, campaign_id: int, driver: MeterDriver, port: str = "") -> None:
        self.ports[campaign_id] = port
        if isinstance(driver, SimulatedMeter):
            self.drivers[campaign_id] = driver

    def driver(self, campaign) -> MeterDriver:
        known = self.drivers.get(campaign["id"])
        if known is not None:
            return known
        if campaign["driver"] == "simulator":
            # After a restart: same clock as before, so stored offsets stay right.
            driver = SimulatedMeter(
                clock_skew_s=campaign["clock_offset_s"], failure_rate=SIMULATED_FAILURE_RATE
            )
            self.drivers[campaign["id"]] = driver
            return driver
        return create_driver(campaign["driver"], port=self.ports.get(campaign["id"], ""))


@dataclass
class AppContext:
    db: Database
    service: CampaignService
    archive: ReportArchive
    devices: DeviceSession = field(default_factory=DeviceSession)


def function_text(key: str) -> str:
    return FUNCTION_LABELS.get(key, key)


def function_short(key: str) -> str:
    return function_text(key).split(" – ")[0]


def verdict_item(verdict: str) -> QTableWidgetItem:
    item = QTableWidgetItem(VERDICT_TEXT[Verdict(verdict)])
    if verdict == Verdict.FAILED.value:
        item.setForeground(QColor("#c0392b"))
        font = item.font()
        font.setBold(True)
        item.setFont(font)
    return item


@contextmanager
def filling(table: QTableWidget):
    """Fill a table in one go.

    A column sized to its contents is measured again after every single cell,
    which makes a visible table with a few hundred rows hang for many seconds.
    """
    header = table.horizontalHeader()
    modes = [header.sectionResizeMode(i) for i in range(header.count())]
    # Sorted while filling, rows would move away under the index being written to.
    sorting = table.isSortingEnabled()
    table.setSortingEnabled(False)
    table.setUpdatesEnabled(False)
    for index in range(header.count()):
        header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
    try:
        yield
    finally:
        for index, mode in enumerate(modes):
            header.setSectionResizeMode(index, mode)
        table.setSortingEnabled(sorting)
        table.setUpdatesEnabled(True)


def make_table(headers: list[str], stretch: int | None = None) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setAlternatingRowColors(True)
    table.verticalHeader().hide()
    # As many rows in view as fit: this is a table to read through, not to tap on.
    table.verticalHeader().setDefaultSectionSize(table.fontMetrics().height() + 8)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    if stretch is not None:
        header.setSectionResizeMode(stretch, QHeaderView.ResizeMode.Stretch)
    return table


def row_of(table: QTableWidget, row_id: int | None) -> int:
    """Where a row is now; sorting moves it. -1 when it is not in the table."""
    for row in range(table.rowCount()):
        if row_id is not None and table.item(row, 0) and table.item(row, 0).data(ROW_ID) == row_id:
            return row
    return -1


def selected_ids(table: QTableWidget) -> list[int]:
    """Every selected row's ID, top to bottom; a line for a run gives all its members."""
    rows = sorted({index.row() for index in table.selectionModel().selectedRows()})
    ids = []
    for row in rows:
        item = table.item(row, 0)
        if item is None:
            continue
        own = item.data(ROW_ID)
        ids += [own] if own is not None else list(item.data(MEMBERS) or ())
    return list(dict.fromkeys(ids))


def selected_id(table: QTableWidget) -> int | None:
    row = table.currentRow()
    item = table.item(row, 0) if row >= 0 else None
    return item.data(ROW_ID) if item else None


class _Task(QThread):
    def __init__(self, work: Callable[[], T], parent=None):
        super().__init__(parent)
        self._work = work
        self.result: T | None = None
        self.error: Exception | None = None

    def run(self) -> None:
        try:
            self.result = self._work()
        except Exception as err:  # handed to the caller on the GUI thread
            self.error = err


def run_busy(parent, text: str, work: Callable[[], T]) -> T:
    """Run slow work off the GUI thread, so the window keeps answering.

    `work` must not touch the database: its connection belongs to the GUI thread.
    Errors come back here and are raised to the caller.
    """
    window = parent.window()
    progress = QProgressDialog(text, "", 0, 0, window)
    progress.setCancelButton(None)
    progress.setWindowTitle("EasyMeasurement")
    progress.setMinimumDuration(300)
    window.setEnabled(False)
    task = _Task(work, window)
    loop = QEventLoop()
    task.finished.connect(loop.quit)
    task.start()
    loop.exec()
    task.wait()
    progress.close()
    window.setEnabled(True)
    if task.error is not None:
        raise task.error
    return task.result


def ask_clock_sync(parent, offset_s: float) -> bool:
    """Whether the program sets the clock or the operator does it on the instrument."""
    box = QMessageBox(QMessageBox.Icon.Question, "Geräteuhr",
                      f"Die Uhr des Messgeräts weicht um {offset_s:+.0f} s ab.",
                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, parent)
    box.button(QMessageBox.StandardButton.Yes).setText("Automatisch stellen")
    box.button(QMessageBox.StandardButton.No).setText("Von Hand stellen")
    return box.exec() == QMessageBox.StandardButton.Yes


def stored_parameters(row) -> list[Parameter]:
    return [Parameter(**item) for item in json.loads(row["parameters_json"])]


def value_line(service, row) -> str:
    """One measurement in a line: which conductors, then what was read."""
    values = "   ".join(
        f"{v['label']} {check_text(v['raw'])}"
        for v in service.values(row["id"])
    )
    conductor = conductor_of(stored_parameters(row))
    return f"{conductor}:  {values}" if conductor else values


def show_error(parent, text: str) -> None:
    QMessageBox.warning(parent, "EasyMeasurement", text)
