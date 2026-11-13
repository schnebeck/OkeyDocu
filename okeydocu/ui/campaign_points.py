# OkeyDocu - okeydocu/ui/campaign_points.py
# A repeat inspection's open points among the measurements, and the point beside the table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ..campaign.repeat import REPEAT
from ..campaign.service import LOCATION_SEPARATOR
from ..model import Verdict
from .common import POINT_ID
from .measurement_overlays import MeasurementOverlay
from .measurement_runs import point_line
from .repeat_compare import RepeatCompare
from .repeat_point import RepeatPoint


class CampaignPoints:
    """Open points stand in the table in grey; chosen, the side shows what to take there."""

    def _build_points(self) -> None:
        self.point = RepeatPoint(self.app)
        self.compare = RepeatCompare(self.app)
        for widget in (self.point, self.compare):
            widget.changed.connect(self._after_change)
        self.point.by_hand.connect(self._point_by_hand)
        self.point.hide()
        holder = QWidget()
        column = QVBoxLayout(holder)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self.editor)
        column.addWidget(self.compare)
        column.addWidget(self.point)
        self.detail = holder
        self.readings, self.files = self.editor.take_out()

    def current_point(self) -> int | None:
        current = self.table.currentItem()
        return self.table.item(current.row(), 0).data(POINT_ID) if current else None

    def point_lines(self, area: list[str]) -> list:
        campaign = self.app.service.campaign(self.campaign_id) if self.campaign_id else None
        if campaign is None or campaign["plan_key"] != REPEAT:
            return []
        below = (set(self.app.service.subtree(self.point_id))
                 if self.point_id is not None else None)
        words = self.find.text().casefold().split()
        lines = []
        for row, step in self.app.service.points(self.campaign_id):
            if row["status"] == "done" or (self.unplaced and step.asset_id is not None):
                continue
            if below is not None and step.asset_id not in below:
                continue
            if not all(word in f"{step.title} {step.question}".casefold() for word in words):
                continue
            path = (self.app.service.place_path(step.asset_id, campaign["asset_id"])
                    .split(LOCATION_SEPARATOR)[1:] if step.asset_id is not None else [])
            if path[:len(area)] == area:
                path = path[len(area):]
            lines.append(point_line(row, step, LOCATION_SEPARATOR.join(path)))
        return lines

    def _show_point_or_measurement(self) -> None:
        """A point shows what to take; a measurement itself and how it compares with last time."""
        point = self.current_point()
        self.point.setVisible(point is not None)
        self.editor.setVisible(point is None)
        if point is not None:
            self.point.show_point(point)
            self.compare.hide()
            target = self.point.step.asset_id
            self.point_chosen.emit(target if target is not None else 0)
        else:
            self.compare.show_measurement(self.editor.row)

    def _point_by_hand(self, step) -> None:
        dialog = MeasurementOverlay(self)
        dialog.function.setCurrentIndex(max(dialog.function.findData(step.function), 0))
        if step.asset_id is not None:
            dialog.location.setText(self.app.service.place_path(step.asset_id))
        if dialog.exec():
            self.app.service.add_measurement(
                self.campaign_id, dialog.function.currentData(), dialog.values(),
                dialog.taken_at(), Verdict(dialog.verdict.currentData()),
                dialog.comment.toPlainText().strip(), dialog.location.text().strip(),
                asset_id=step.asset_id,
            )
            self._after_change()
