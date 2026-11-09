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
    QTableWidgetItem,
    QToolButton,
    QWidget,
)

from ..campaign.service import LOCATION_SEPARATOR
from ..model import conductor_of
from ..store.search import MeasurementFilter, search_measurements
from .common import (
    ROW_ID,
    AppContext,
    filling,
    function_short,
    make_table,
    row_of,
    selected_id,
    stored_parameters,
    verdict_item,
)
from .measurement_detail import THUMB, MeasurementDetail, capture_text
from .measurement_editor import MeasurementEditor
from .photo_shared import shared_thumbs
from .report_signing import settings
from .table_columns import SortItem, TableColumns

CUSTOMER, ASSET, CAMPAIGN = 1, 2, 3
_PLACE, _VALUES, _VERDICT = 4, 6, 8
_CAPTURE = 9
_SHARED_COLUMNS = {
    CUSTOMER: "Kunde", ASSET: "Anlage", CAMPAIGN: "Kampagne", _PLACE: "Messort", 5: "Funktion",
    7: "Fotos", _VERDICT: "Bewertung", _CAPTURE: "Erfassung",
}


def _values(row) -> str:
    """Only some functions have a conductor, so it stands with the reading it belongs to."""
    values = row["value_text"] or ""
    conductor = conductor_of(stored_parameters(row))
    return f"{conductor}:  {values}" if conductor else values


def _path(row) -> list[str]:
    """Where in the installation, without repeating the installation itself."""
    parts = row["location"].split(LOCATION_SEPARATOR) if row["location"] else []
    return parts[1:] if parts[:1] == [row["asset_name"]] else parts


def _sort_key(column: int, row):
    """Time and photos sort as what they are; values by function first, then by size."""
    if column == 0:
        return (row["local_time"], row["id"])
    if column == 7:
        return row["photo_count"] or 0
    if column == _VALUES:
        first = row["first_value"]
        return (row["function"] or "", float("inf") if first is None else first)
    return None


def _shared_start(paths: list[list[str]]) -> list[str]:
    """What all paths begin with. The last part of each stays, it names the place."""
    shared = []
    for parts in zip(*(path[:-1] for path in paths)):
        if len(set(parts)) > 1:
            break
        shared.append(parts[0])
    return shared


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
            ["Zeitpunkt", "Kunde", "Anlage", "Kampagne", "Messort", "Funktion", "Messwerte",
             "Fotos", "Bewertung", "Erfassung"],
            stretch=_VALUES,
        )
        # The values are what this table is for, so names give way and can be widened.
        header = self.table.horizontalHeader()
        for column, width in ((CUSTOMER, 110), (ASSET, 110), (CAMPAIGN, 120), (_PLACE, 180)):
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
        self.table.cellDoubleClicked.connect(self._cell_double_clicked)
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
        # The search returns the newest first, so a limit keeps the recent ones.
        # Read as a record, the day runs from top to bottom.
        query = self.current_filter()
        rows = list(reversed(search_measurements(self.app.db, query))) if query else []
        moments = [datetime.fromisoformat(row["local_time"]) for row in rows]
        one_day = len(rows) > 1 and len({moment.date() for moment in moments}) == 1
        paths = [_path(row) for row in rows]
        area = _shared_start(paths) if len(rows) > 1 else []
        time_format = "%H:%M:%S" if one_day else "%d.%m.%Y %H:%M:%S"
        with filling(self.table):
            self.table.setRowCount(len(rows))
            for index, row in enumerate(rows):
                cells = [
                    moments[index].strftime(time_format), row["customer_name"], row["asset_name"],
                    row["campaign_title"], LOCATION_SEPARATOR.join(paths[index][len(area):]),
                    function_short(row["function"]),
                    _values(row), str(row["photo_count"] or ""),
                ]
                for column, text in enumerate(cells):
                    self.table.setItem(index, column, SortItem(text, _sort_key(column, row)))
                self.table.setItem(index, _VERDICT, verdict_item(row["verdict"]))
                self.table.setItem(index, _CAPTURE, QTableWidgetItem(capture_text(row)))
                self.table.item(index, 0).setData(ROW_ID, row["id"])
        self._move_common_to_head(
            f"{moments[0]:%d.%m.%Y}" if one_day else "", LOCATION_SEPARATOR.join(area)
        )
        self.count.setText("1 Messung" if len(rows) == 1 else f"{len(rows)} Messungen")
        restore = row_of(self.table, selected)
        if restore >= 0:
            self.table.setCurrentCell(restore, 0)
        self._show_detail()

    def _move_common_to_head(self, day: str, area: str) -> None:
        """What every row shares is said once above the table, not in each line."""
        rows = self.table.rowCount()
        shared = [("Datum", day)] if day else []
        if area:
            shared.append(("Bereich", area))
        alike = {}
        for column in _SHARED_COLUMNS:
            texts = {self.table.item(row, column).text() for row in range(rows)}
            if rows > 1 and len(texts) == 1:
                alike[column] = texts.pop()
        gathered = self.columns.apply(set(alike))
        shared += [(label, alike[column]) for column, label in _SHARED_COLUMNS.items()
                   if column in gathered and alike[column]]
        self.common.setText(
            " &nbsp;·&nbsp; ".join(f"{label}: <b>{escape(text)}</b>" for label, text in shared)
        )
        self.common.setVisible(bool(shared))
