# OkeyDocu - okeydocu/ui/measurement_menu.py
# The context menu of a table of measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMessageBox

from ..l10n import tr
from ..model import conductor_of
from .common import selected_id, selected_ids, stored_parameters
from .measurement_details import MeasurementDetails
from .table_columns import GROUP


PATHS = ("L1-PE", "L2-PE", "L3-PE", "N-PE", "L1-N", "L2-N", "L3-N", "L1-L2", "L2-L3", "L1-L3")
PATH_QUERY = ("SELECT m.parameters_json, c.status FROM measurements m"
              " JOIN campaigns c ON c.id = m.campaign_id WHERE m.id=?")


class RowMenu:
    """A right click on a row offers what may be done to it; first, to see how it was taken.
    With several rows selected it offers only what applies to all of them at once, as the
    structure tree does."""

    def _set_up_row_menu(self) -> None:
        self.details_action = QAction(tr("How it was measured …"), self)
        self.details_action.triggered.connect(self._show_measuring)
        self.plan_action = QAction(tr("Take over as test plan"), self)
        self.plan_action.setToolTip(tr("The sequence becomes a draft test plan with the same"
                                       " questions and measurements"))
        self.plan_action.triggered.connect(self._take_over_plan)
        self.path_action = QAction(tr("Change measuring path"), self)
        self.path_action.setToolTip(tr("Sets right between which conductors the measurement was"
                                       " taken. The readings stay; the change is logged."))
        paths = QMenu(self)
        for pair in PATHS:
            paths.addAction(pair).triggered.connect(partial(self._set_path, pair))
        self.path_action.setMenu(paths)
        self.menu_run: int | None = None
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._row_menu)

    def _menu_actions(self) -> tuple:
        """Actions in their order; None draws a line between them."""
        taken = (self.plan_action, None) if self.menu_run is not None else ()
        return (self.details_action, None, *taken, self.edit_action, *self.path_actions(),
                self.photo_action, None, self.delete_action)

    def _many_actions(self) -> tuple:
        """Actions for several rows at once."""
        return (*self.path_actions(), self.delete_action)

    def path_actions(self) -> tuple:
        """The measuring path may be set right where every chosen row names one and its
        campaign is still open."""
        rows = [self.app.db.one(PATH_QUERY, chosen) for chosen in selected_ids(self.table)]
        named = rows and all(row and row["status"] == "open"
                             and conductor_of(stored_parameters(row)) for row in rows)
        return (self.path_action,) if named else ()

    def _set_path(self, pair: str, *_) -> None:
        for chosen in selected_ids(self.table):
            self.app.service.set_conductor(chosen, pair)
        self._after_change()

    def _row_menu(self, point) -> None:
        row = self.table.indexAt(point).row()
        if row < 0:
            return
        self.note_run(row)
        count = len(selected_ids(self.table))
        single = self.delete_action.text()
        if count > 1:
            self.delete_action.setText(tr("Delete {count} measurements …", count=count))
        menu = QMenu(self)
        for action in self._many_actions() if count > 1 else self._menu_actions():
            menu.addSeparator() if action is None else menu.addAction(action)
        menu.exec(self.table.viewport().mapToGlobal(point))
        menu.deleteLater()
        self.delete_action.setText(single)

    def note_run(self, row: int) -> None:
        """The run a row belongs to, which the menu may take over as a plan."""
        first = self.table.item(row, 0)
        self.menu_run = first.data(GROUP) if first is not None else None

    def _show_measuring(self) -> None:
        measurement_id = selected_id(self.table)
        if measurement_id is not None:
            MeasurementDetails(self.app, measurement_id, self).exec()

    def _take_over_plan(self) -> None:
        if self.menu_run is None:
            return
        title = self.app.service.plan_from_run(self.menu_run)
        QMessageBox.information(self, tr("Test plan created"), tr(
            "“{title}” is now among the test plans, as a draft. It can be checked and released"
            " under Settings → Test plans and assigned to any campaign.", title=title))
