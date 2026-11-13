# OkeyDocu - okeydocu/ui/measurement_menu.py
# The context menu of a table of measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QMessageBox

from ..l10n import tr
from .common import selected_id
from .measurement_details import MeasurementDetails
from .table_columns import GROUP


class RowMenu:
    """A right click on a row offers what may be done to it; first, to see how it was taken."""

    def _set_up_row_menu(self) -> None:
        self.details_action = QAction(tr("How it was measured …"), self)
        self.details_action.triggered.connect(self._show_measuring)
        self.plan_action = QAction(tr("Take over as test plan"), self)
        self.plan_action.setToolTip(tr("The sequence becomes a draft test plan with the same"
                                       " questions and measurements"))
        self.plan_action.triggered.connect(self._take_over_plan)
        self.menu_run: int | None = None
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._row_menu)

    def _menu_actions(self) -> tuple:
        """Actions in their order; None draws a line between them."""
        taken = (self.plan_action, None) if self.menu_run is not None else ()
        return (self.details_action, None, *taken, self.edit_action, self.photo_action, None,
                self.delete_action)

    def _row_menu(self, point) -> None:
        row = self.table.indexAt(point).row()
        if row < 0:
            return
        self.note_run(row)
        menu = QMenu(self)
        for action in self._menu_actions():
            menu.addSeparator() if action is None else menu.addAction(action)
        menu.exec(self.table.viewport().mapToGlobal(point))
        menu.deleteLater()

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
