# OkeyDocu - okeydocu/ui/structure_drop.py
# Dropping onto the structure tree: elements move, measurement rows are booked onto an element.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt

from .common import ROW_ID, selected_ids

UNPLACED = -1  # the item for measurements booked onto no element


class StructureDrop:
    """Drag and drop of the structure tree; the tree supplies items, selection and `_apply`."""

    def dragEnterEvent(self, event) -> None:
        if event.source() is self or (self.bookable and event.source() is self.measurement_source):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event) -> None:
        super().dragMoveEvent(event)
        target = self.itemAt(event.position().toPoint())
        valid = target is not None and target.data(0, ROW_ID) != UNPLACED
        if target is None and event.source() is self and self.customer_id is not None:
            valid = True  # onto the empty area: to the top of the customer
        elif valid and event.source() is self:
            valid = target.data(0, ROW_ID) not in self.selected_ids()
        event.setAccepted(valid)

    def dropEvent(self, event) -> None:
        target = self.itemAt(event.position().toPoint())
        to_top = target is None and event.source() is self and self.customer_id is not None
        if not to_top and (target is None or target.data(0, ROW_ID) == UNPLACED):
            event.ignore()
            return
        target_id = None if to_top else target.data(0, ROW_ID)
        if event.source() is self:
            moving = [i for i in self.selected_ids() if i != self.root_id]
            self._apply(lambda: [self.app.service.move_element(i, target_id) for i in moving])
        else:
            ids = selected_ids(self.measurement_source)
            self._apply(lambda: self.app.service.move_measurements(ids, target_id))
        # Copy, not move: the views rebuild from the database, nothing is to be removed.
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()
