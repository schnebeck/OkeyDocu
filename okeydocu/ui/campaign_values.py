# OkeyDocu - okeydocu/ui/campaign_values.py
# The measurements of the campaign on screen, narrowed to a point or a step.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QLineEdit,
    QSizePolicy,
    QVBoxLayout,
)

from ..l10n import tr
from ..model import Verdict
from ..store.search import MeasurementFilter
from .board import Strip
from .campaign_points import CampaignPoints
from .common import ROW_ID, RUN_ID, AppContext, row_of, selected_ids
from .measurement_overlays import MeasurementOverlay
from .measurement_view import ASSET, CAMPAIGN, CUSTOMER, MeasurementView
from .move_overlay import MoveOverlay


class CampaignValues(CampaignPoints, MeasurementView):
    """The measurements of one campaign, with what it is known for repeated nowhere."""

    named_columns = (CUSTOMER, ASSET, CAMPAIGN)
    place_requested = Signal(int)  # the element of the measurement should be shown
    point_chosen = Signal(int)  # new readings belong to this element now (0: the whole)
    detail_shown = Signal(bool, int, str)  # a row is chosen; its photos; the run of the line

    def __init__(self, app: AppContext):
        super().__init__(app)
        self._build_points()
        self.campaign_id: int | None = None
        self.point_id: int | None = None
        self.unplaced = False  # only what is booked onto no element
        self.step_id: int | None = None
        self.in_plan = False  # a plan is being run: readings typed by hand go to its step
        self.manual_action, self.manual_button = self._action(
            tr("Reading by hand …"), tr("By hand …"), self._enter_by_hand
        )
        # Made after the others, the button came last; it belongs first, always in one place.
        self.actions_row.removeWidget(self.manual_button)
        self.actions_row.insertWidget(0, self.manual_button)
        # What all rows share and how many there are: a line across the whole board, so
        # the board places it (`head`) above the structure and the table alike.
        self.actions_row.removeWidget(self.count)
        self.common.setWordWrap(False)
        self.common.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.head = Strip(ruled=False)
        self.head.row.setContentsMargins(8, 5, 8, 1)
        # The filter sits with what it narrows; in the tools it would push them aside.
        self.head.row.addWidget(self.common, 1)
        self.head.row.addStretch(0)  # keeps the right end in place while `common` is hidden
        self.head.row.addWidget(self.count)
        # Row actions live in the row's context menu and on keys; the bar keeps entering
        # by hand and a filter, so nothing in it stands grey most of the time.
        for button in (self.edit_measurement, self.delete_measurement, self.add_photo):
            button.hide()
        self.move_action = QAction(tr("Move to …"), self)
        self.move_action.triggered.connect(self._move_to)
        self.table.itemSelectionChanged.connect(self._update_move)
        self.editor.movable = True
        self.editor.place.move_requested.connect(self._move_to)
        self.editor.place.chosen.connect(self.place_requested)
        self.find = QLineEdit(placeholderText=tr("Filter readings …"))
        self.find.setClearButtonEnabled(True)
        self.find.setFixedWidth(260)
        self._typing = QTimer(self, singleShot=True, interval=250)
        self._typing.timeout.connect(self.refresh)
        self.find.textChanged.connect(lambda: self._typing.start())
        self.actions_row.addWidget(self.find)
        self.bar = Strip(self.actions_row)
        self.bar.even_out()
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.bar)
        layout.addWidget(self.table, 1)
        # Rows are dragged onto the structure to book them there; several at once.
        self.table.setDragEnabled(True)
        self.table.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.refresh()

    def show_campaign(self, campaign_id: int) -> None:
        if campaign_id != self.campaign_id:
            self.find.blockSignals(True)
            self.find.clear()  # a filter belongs to the campaign it was typed for
            self.find.blockSignals(False)
        self.campaign_id = campaign_id
        self.point_id, self.unplaced = None, False
        self.refresh()

    def show_point(self, asset_id: int | None) -> None:
        self.point_id, self.unplaced = asset_id, False
        self.refresh()

    def show_unplaced(self) -> None:
        self.point_id, self.unplaced = None, True
        self.refresh()

    def show_step(self, step_id: int | None) -> None:
        self.step_id = step_id

    def select_measurement(self, measurement_id: int) -> None:
        """A step of a folded run opens the run first, so the step can be seen."""
        row = row_of(self.table, measurement_id)
        if row < 0:
            found = self.app.db.one("SELECT run_id FROM measurements WHERE id=?", measurement_id)
            if found and found["run_id"] is not None and found["run_id"] not in self.open_runs:
                self.toggle_run(found["run_id"])
                row = row_of(self.table, measurement_id)
        if row >= 0:
            self.table.selectRow(row)
            self.table.scrollToItem(self.table.item(row, 0))

    def show_newest(self) -> None:
        """A reading just came in: this is the one to look at, unless one is being corrected."""
        if self.table.rowCount() and not self.editor.dirty:
            # Wherever the sorting put it, the newest reading has the highest number.
            row = max(range(self.table.rowCount()),
                      key=lambda row: self.table.item(row, 0).data(ROW_ID) or -1)
            self.table.selectRow(row)
            self.table.scrollToItem(self.table.item(row, 0))

    def current_filter(self) -> MeasurementFilter | None:
        if self.campaign_id is None:
            return None
        return MeasurementFilter(
            text=self.find.text().strip(),
            campaign_id=self.campaign_id, point_id=self.point_id, unplaced=self.unplaced,
        )

    def _show_detail(self) -> None:
        super()._show_detail()
        self._show_point_or_measurement()
        current = self.table.currentItem()
        run = self.table.item(current.row(), 0).data(RUN_ID) if current else None
        name = self.app.service.run(run)["name"] if run is not None else ""
        chosen = self.editor.row is not None or self.current_point() is not None
        self.detail_shown.emit(chosen, self.gallery.count(), name)

    def _move_common_to_head(self, day: str, area: str) -> None:
        super()._move_common_to_head(day, area)
        self.common.setToolTip(self.common.text())

    def _update_actions(self, row) -> None:
        super()._update_actions(row)
        campaign = self.app.service.campaign(self.campaign_id) if self.campaign_id else None
        is_open = bool(campaign) and campaign["status"] == "open"
        self.manual_action.setEnabled(is_open)
        self._update_move()
        self.manual_button.setVisible(is_open)

    def _update_move(self) -> None:
        campaign = self.app.service.campaign(self.campaign_id) if self.campaign_id else None
        is_open = bool(campaign) and campaign["status"] == "open"
        self.move_action.setEnabled(is_open and bool(selected_ids(self.table)))

    def _menu_actions(self) -> tuple:
        taken = (self.plan_action, None) if self.menu_run is not None else ()
        return (self.details_action, None, *taken, self.edit_action, self.photo_action,
                self.move_action, None, self.delete_action)

    def _move_to(self) -> None:
        ids = selected_ids(self.table)
        root = self.app.service.campaign(self.campaign_id)["asset_id"]
        current = self.app.db.one("SELECT asset_id FROM measurements WHERE id=?", ids[0])
        overlay = MoveOverlay(self.app, root, len(ids), current["asset_id"], self)
        if overlay.exec():
            self.app.service.move_measurements(ids, overlay.chosen())
            self._after_change()

    def _place_path(self) -> str:
        root = self.app.service.campaign(self.campaign_id)["asset_id"]
        return self.app.service.place_path(self.point_id, root)

    def _enter_by_hand(self) -> None:
        dialog = MeasurementOverlay(self)
        if self.point_id is not None:
            dialog.location.setText(self._place_path())
        if dialog.exec():
            self.app.service.add_measurement(
                self.campaign_id, dialog.function.currentData(), dialog.values(),
                dialog.taken_at(), Verdict(dialog.verdict.currentData()),
                dialog.comment.toPlainText().strip(),
                dialog.location.text().strip(),
                step_id=self.step_id if self.in_plan else None,
                asset_id=self.point_id,
            )
            self._after_change()
