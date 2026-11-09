# EasyMeasurement - easymeasurement/ui/campaign_photos.py
# The photo timeline and stack of the campaign on screen, tied to its measurement table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from .common import ROW_ID, selected_id
from .photo_shared import accept_photo_drops
from .photo_stack import PhotoStack
from .photo_timeline import PhotoTimeline


class CampaignPhotos:
    """The timeline appears once a campaign has photos, so it never takes room for nothing."""

    def _build_photos(self) -> None:
        self.timeline = PhotoTimeline(self.app)
        self.timeline.hide()
        self.stack = PhotoStack(self.app)
        self.timeline.changed.connect(self._photos_changed)
        self.stack.changed.connect(self._photos_changed)
        self.timeline.measurement_chosen.connect(self._select_measurement)

    def _connect_photos(self) -> None:
        table = self.values.table
        table.currentCellChanged.connect(
            lambda *_: self.timeline.select_measurement(selected_id(table))
        )
        self.photo_drops = accept_photo_drops(
            table.viewport(), self._photo_dropped, allowed=self._row_takes_photo
        )

    def _row_takes_photo(self, position) -> bool:
        campaign = self._campaign()
        open_campaign = bool(campaign) and campaign["status"] == "open"
        return open_campaign and self.values.table.indexAt(position).isValid()

    def _photo_dropped(self, photo_id: int, position) -> None:
        table = self.values.table
        row = table.indexAt(position).row()
        self.app.service.pin_photo(photo_id, table.item(row, 0).data(ROW_ID))
        self._photos_changed()

    def _select_measurement(self, measurement_id: int) -> None:
        table = self.values.table
        for row in range(table.rowCount()):
            if table.item(row, 0).data(ROW_ID) == measurement_id:
                table.selectRow(row)
                table.scrollToItem(table.item(row, 0))
                return

    def _show_photos(self, campaign_id: int) -> None:
        self.timeline.show_campaign(campaign_id)
        self.stack.show_campaign(campaign_id)
        self._fit_photo_panels()

    def _fit_photo_panels(self) -> None:
        photos = self.app.service.photos(self.campaign_id) if self.campaign_id else []
        placed = any(row["placement"] != "stack" for row in photos)
        self.timeline.setVisible(placed and self.timeline_action.isChecked())
        self.timeline_action.setEnabled(placed)
        self.stack_section.setVisible(self.stack.count > 0)
        self.stack_section.set_count(self.stack.count)

    def _refresh_photos(self) -> None:
        """After a change of the measurements, which the timeline shows as well."""
        if self.campaign_id is not None:
            self.timeline.refresh()
            self.stack.refresh()
            self._fit_photo_panels()

    def _photos_changed(self) -> None:
        self.guided.reload()
        self._data_changed()
