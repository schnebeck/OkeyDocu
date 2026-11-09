# EasyMeasurement - easymeasurement/ui/measurement_view.py
# The table of measurements shared by the campaign workspace and the search.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QToolButton,
    QWidget,
)

from ..campaign.service import LOCATION_SEPARATOR
from ..store.search import MeasurementFilter, search_measurements
from .common import (
    POINT_ID,
    RUN_ID,
    AppContext,
    filling,
    make_table,
    row_of,
    selected_id,
)
from .measurement_cells import (
    ASSET,
    CAMPAIGN,
    CUSTOMER,
    PLACE,
    SHARED_COLUMNS,
    VALUES,
    path_of,
    shared_start,
)
from .measurement_detail import THUMB, MeasurementDetail
from .measurement_editor import MeasurementEditor
from .measurement_runs import table_lines, write_line
from .photo_shared import shared_thumbs
from .report_signing import settings
from .table_columns import TableColumns
from .verdict_marks import MARK_SIZE

class MeasurementView(MeasurementDetail, QWidget):
    """The table, what the selected row holds, and what may be done to it."""

    changed = Signal()
    edit_requested = Signal()  # the field beside the table should come into view
    named_columns = ()  # said elsewhere on the screen, so neither column nor head repeats them

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.count = QLabel()
        self.table = make_table(
            ["Zeitpunkt", "Kunde", "Anlage", "Kampagne", "Messort", "Bezeichnung", "Messwerte",
             "Fotos", "Bewertung", "Erfassung"],
            stretch=VALUES,
        )
        # The values are what this table is for, so names give way and can be widened.
        header = self.table.horizontalHeader()
        for column, width in ((CUSTOMER, 110), (ASSET, 110), (CAMPAIGN, 120), (PLACE, 180)):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
            key = f"columns/{type(self).__name__}/{column}"
            header.resizeSection(column, settings().value(key, width, type=int))
        # A width dragged by hand is kept for the next start.
        header.sectionResized.connect(self._keep_width)
        self.columns = TableColumns(self.table, type(self).__name__, self.named_columns)
        self.columns.changed.connect(self.refresh)
        self.common = QLabel()
        self.common.setWordWrap(True)
        self.common.setTextFormat(Qt.TextFormat.RichText)
        self.table.currentCellChanged.connect(lambda *_: self._show_detail())
        self.open_runs: set[int] = set()  # runs whose steps are shown one by one
        self.table.setIconSize(MARK_SIZE)
        self.table.cellClicked.connect(lambda row, column: self._clicked(row, column, False))
        self.table.cellDoubleClicked.connect(lambda row, column: self._clicked(row, column, True))
        # On the table, Enter goes to the field beside it and Delete asks to delete the row.
        for key, slot in ((Qt.Key.Key_Return, self._edit_measurement),
                          (Qt.Key.Key_Enter, self._edit_measurement),
                          (Qt.Key.Key_Delete, self._delete_measurement)):
            shortcut = QShortcut(QKeySequence(key), self.table)
            shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
            shortcut.activated.connect(lambda slot=slot: self._by_key(slot))
        self.editor = MeasurementEditor(app)
        self.editor.changed.connect(self._after_change)
        self.detail = self.editor
        self.values = self.editor.values
        self.gallery = QListWidget()
        self.gallery.setViewMode(QListWidget.ViewMode.IconMode)
        self.gallery.setIconSize(QPixmap(THUMB, THUMB).size())
        self.gallery.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.gallery.setMovement(QListWidget.Movement.Static)
        shared_thumbs().ready.connect(self._thumb_ready)
        self.gallery.itemActivated.connect(self._preview_photo)

        self.actions_row = QHBoxLayout()
        self.edit_action, self.edit_measurement = self._action(
            "Messung bearbeiten", "Bearbeiten", self._edit_measurement
        )
        self.edit_action.setShortcut("F2")
        self.delete_action, self.delete_measurement = self._action(
            "Messung löschen …", "Löschen …", self._delete_measurement
        )
        self.photo_action, self.add_photo = self._action(
            "Foto zur Messung …", "Foto …", self._add_photo
        )
        self.actions_row.addStretch()
        self.actions_row.addWidget(self.count)

    def point_lines(self, area: list[str]) -> list:
        """Lines for what is still to be taken; only a repeat inspection has them."""
        return []

    def toggle_run(self, run_id: int) -> None:
        """A run's steps open under its line, or fold back into it."""
        (self.open_runs.discard if run_id in self.open_runs else self.open_runs.add)(run_id)
        self.refresh()

    def _run_row(self, run_id: int | None) -> int:
        for row in range(self.table.rowCount()):
            if run_id is not None and self.table.item(row, 0).data(RUN_ID) == run_id:
                return row
        return -1

    def _clicked(self, row: int, column: int, double: bool) -> None:
        run = self.table.item(row, 0).data(RUN_ID)
        if run is not None and (double or column == 0):
            self.toggle_run(run)
        elif double:
            self._cell_double_clicked(row, column)

    def _keep_width(self, column: int, _old: int, new: int) -> None:
        mode = self.table.horizontalHeader().sectionResizeMode(column)
        if mode == QHeaderView.ResizeMode.Interactive and new > 0:
            settings().setValue(f"columns/{type(self).__name__}/{column}", new)

    def _action(self, text: str, short: str, slot) -> tuple[QAction, QToolButton]:
        """One action behind both button and menu, so they cannot disagree.

        The menu needs the whole name, the button stands next to the table it acts on.
        """
        action = QAction(text, self)
        action.setIconText(short)
        action.triggered.connect(lambda: slot())
        button = QToolButton()
        button.setDefaultAction(action)
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self.actions_row.addWidget(button)
        return action, button

    def current_filter(self) -> MeasurementFilter | None:
        raise NotImplementedError

    def refresh(self) -> None:
        selected = selected_id(self.table)
        current = self.table.currentItem()
        run = self.table.item(current.row(), 0).data(RUN_ID) if current else None
        # The search returns the newest first, so a limit keeps the recent ones.
        # Read as a record, the day runs from top to bottom.
        query = self.current_filter()
        rows = list(reversed(search_measurements(self.app.db, query))) if query else []
        moments = [datetime.fromisoformat(row["local_time"]) for row in rows]
        one_day = len(rows) > 1 and len({moment.date() for moment in moments}) == 1
        paths = [path_of(row) for row in rows]
        area = shared_start(paths) if len(rows) > 1 else []
        time_format = "%H:%M:%S" if one_day else "%d.%m.%Y %H:%M:%S"
        lines = table_lines(rows, self.open_runs, time_format, area, paths)
        points = self.point_lines(area)
        lines += points
        with filling(self.table):
            self.table.setRowCount(len(lines))
            for index, line in enumerate(lines):
                write_line(self.table, index, line)
        self._move_common_to_head(
            f"{moments[0]:%d.%m.%Y}" if one_day else "", LOCATION_SEPARATOR.join(area)
        )
        self.count.setText(("1 Messung" if len(rows) == 1 else f"{len(rows)} Messungen")
                           + (f"  ·  {len(points)} offen" if points else ""))
        restore = row_of(self.table, selected) if selected is not None else self._run_row(run)
        if restore >= 0:
            self.table.setCurrentCell(restore, 0)
        self._show_detail()

    def _move_common_to_head(self, day: str, area: str) -> None:
        """What every row shares is said once above the table, not in each line."""
        # Points still to be taken have no values yet, only a place and a name to tell.
        rows = [row for row in range(self.table.rowCount())
                if self.table.item(row, 0).data(POINT_ID) is None]
        points = [row for row in range(self.table.rowCount()) if row not in rows]
        shared = [("Datum", day)] if day else []
        if area:
            shared.append(("Bereich", area))
        alike = {}
        for column in SHARED_COLUMNS:
            told = rows + (points if column in (PLACE, 5) else [])
            texts = {self.table.item(row, column).text() for row in told}
            if len(told) > 1 and len(texts) == 1:
                alike[column] = texts.pop()
        gathered = self.columns.apply(set(alike))
        shared += [(label, alike[column]) for column, label in SHARED_COLUMNS.items()
                   if column in gathered and alike[column]]
        self.common.setText(
            " &nbsp;·&nbsp; ".join(f"{label}: <b>{escape(text)}</b>" for label, text in shared)
        )
        self.common.setVisible(bool(shared))
