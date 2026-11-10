# EasyMeasurement - easymeasurement/ui/measurement_menu.py
# The context menu of a table of measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu

from ..l10n import tr
from .common import selected_id
from .measurement_details import MeasurementDetails


class RowMenu:
    """A right click on a row offers what may be done to it; first, to see how it was taken."""

    def _set_up_row_menu(self) -> None:
        self.details_action = QAction(tr("How it was measured …"), self)
        self.details_action.triggered.connect(self._show_measuring)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._row_menu)

    def _menu_actions(self) -> tuple:
        """Actions in their order; None draws a line between them."""
        return (self.details_action, None, self.edit_action, self.photo_action, None,
                self.delete_action)

    def _row_menu(self, point) -> None:
        if self.table.indexAt(point).row() < 0:
            return
        menu = QMenu(self)
        for action in self._menu_actions():
            menu.addSeparator() if action is None else menu.addAction(action)
        menu.exec(self.table.viewport().mapToGlobal(point))
        menu.deleteLater()

    def _show_measuring(self) -> None:
        measurement_id = selected_id(self.table)
        if measurement_id is not None:
            MeasurementDetails(self.app, measurement_id, self).exec()
