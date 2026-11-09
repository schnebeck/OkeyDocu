# EasyMeasurement - easymeasurement/ui/campaign_values.py
# The measurements of the campaign on screen, narrowed to a point or a step.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QCheckBox, QFrame, QSizePolicy, QVBoxLayout

from ..model import Verdict
from ..store.search import MeasurementFilter
from .board import Strip
from .common import ROW_ID, AppContext
from .measurement_overlays import MeasurementOverlay
from .measurement_view import ASSET, CAMPAIGN, CUSTOMER, MeasurementView


class CampaignValues(MeasurementView):
    """The measurements of one campaign, with what it is known for repeated nowhere."""

    named_columns = (CUSTOMER, ASSET, CAMPAIGN)

    def __init__(self, app: AppContext):
        super().__init__(app)
        self.campaign_id: int | None = None
        self.point_id: int | None = None
        self.unplaced = False  # only what is booked onto no element
        self.step_id: int | None = None
        self.manual_action, self.manual_button = self._action(
            "Messwert von Hand …", "Von Hand …", self._enter_by_hand
        )
        self.only_step = QCheckBox("Nur dieser Schritt")
        self.only_step.toggled.connect(lambda: self.refresh())
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
        self.head.row.addWidget(self.only_step)
        self.head.row.addSpacing(12)
        self.head.row.addWidget(self.count)
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

    def show_campaign(self, campaign_id: int, with_steps: bool = False, by_step: bool = False) -> None:
        self.campaign_id = campaign_id
        self.point_id, self.unplaced = None, False
        self.only_step.blockSignals(True)
        self.only_step.setChecked(by_step)
        self.only_step.blockSignals(False)
        self.only_step.setVisible(with_steps)
        self.refresh()

    def show_point(self, asset_id: int | None) -> None:
        self.point_id, self.unplaced = asset_id, False
        self.refresh()

    def show_unplaced(self) -> None:
        self.point_id, self.unplaced = None, True
        self.refresh()

    def show_step(self, step_id: int | None) -> None:
        self.step_id = step_id
        if self.only_step.isChecked():
            self.refresh()

    def show_newest(self) -> None:
        """A reading just came in: this is the one to look at, unless one is being corrected."""
        if self.table.rowCount() and not self.editor.dirty:
            # Wherever the sorting put it, the newest reading has the highest number.
            row = max(range(self.table.rowCount()),
                      key=lambda row: self.table.item(row, 0).data(ROW_ID))
            self.table.selectRow(row)
            self.table.scrollToItem(self.table.item(row, 0))

    def current_filter(self) -> MeasurementFilter | None:
        if self.campaign_id is None:
            return None
        narrowed = self.only_step.isChecked() and self.step_id is not None
        return MeasurementFilter(
            campaign_id=self.campaign_id, point_id=self.point_id, unplaced=self.unplaced,
            step_id=self.step_id if narrowed else None,
        )

    def _move_common_to_head(self, day: str, area: str) -> None:
        super()._move_common_to_head(day, area)
        self.common.setToolTip(self.common.text())

    def _update_actions(self, row) -> None:
        super()._update_actions(row)
        campaign = self.app.service.campaign(self.campaign_id) if self.campaign_id else None
        is_open = bool(campaign) and campaign["status"] == "open"
        self.manual_action.setEnabled(is_open)
        # A closed record offers nothing to do, so its buttons leave the row to the count.
        for button in (self.manual_button, self.edit_measurement, self.delete_measurement,
                       self.add_photo):
            button.setVisible(is_open)

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
                step_id=self.step_id if self.only_step.isChecked() else None,
                asset_id=self.point_id,
            )
            self._after_change()
