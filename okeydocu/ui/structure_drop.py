# OkeyDocu - okeydocu/ui/structure_drop.py
# Dropping onto the structure tree: elements move, measurements are booked, photos are laid.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QAbstractItemView

from .common import ROW_ID, selected_ids
from .photo_shared import PHOTO_MIME, dropped_photo
from .photo_to_place import place_photo

Position = QAbstractItemView.DropIndicatorPosition
UNPLACED = -1  # the item for measurements booked onto no element


class StructureDrop:
    """Drag and drop of the structure tree; the tree supplies items, selection and `_apply`."""

    def mimeTypes(self) -> list[str]:
        """A photo counts as droppable, so the tree marks the element it is carried over."""
        return [*super().mimeTypes(), PHOTO_MIME]

    def _carries(self, event) -> bool:
        """Something of an open campaign: rows of its table or one of its photos."""
        return self.bookable and (event.source() is self.measurement_source
                                  or dropped_photo(event.mimeData()) is not None)

    def dragEnterEvent(self, event) -> None:
        if event.source() is self or self._carries(event):
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
        photo = dropped_photo(event.mimeData())
        if photo is not None:
            # Once the drag is over: laying it there may ask a question first.
            QTimer.singleShot(0, lambda: self._apply(
                lambda: place_photo(self, self.app.service, photo, target_id)))
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        if event.source() is self:
            moving = [i for i in self.selected_ids() if i != self.root_id]
            beside = self._beside(target_id)
            if beside is None:
                self._apply(lambda: [self.app.service.move_element(i, target_id) for i in moving])
            else:
                self._apply(lambda: self._place(moving, target_id, beside))
        else:
            ids = selected_ids(self.measurement_source)
            self._apply(lambda: self.app.service.move_measurements(ids, target_id))
        # Copy, not move: the views rebuild from the database, nothing is to be removed.
        event.setDropAction(Qt.DropAction.CopyAction)
        event.accept()

    def _beside(self, target_id) -> bool | None:
        """Dropped on the line above or below an element: True after it, False before it;
        None dropped onto it. The installation a campaign shows has nothing beside it."""
        where = self.dropIndicatorPosition()
        if target_id is None or target_id == self.root_id or \
                where not in (Position.AboveItem, Position.BelowItem):
            return None
        return where == Position.BelowItem

    def _place(self, moving: list[int], target_id: int, after: bool) -> None:
        """The dragged elements keep their order among themselves."""
        for asset_id in reversed(moving) if after else moving:
            self.app.service.place_element(asset_id, target_id, after)
