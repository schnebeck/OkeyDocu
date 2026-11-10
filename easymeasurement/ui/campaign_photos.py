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
        self.timeline.close_requested.connect(lambda: self.timeline_action.setChecked(False))

    def _connect_photos(self) -> None:
        table = self.values.table
        table.currentCellChanged.connect(
            lambda *_: self.timeline.select_measurement(selected_id(table))
        )
        self.photo_drops = accept_photo_drops(
            table.viewport(), self._photo_dropped, allowed=self._row_takes_photo
        )
        self.values.detail_shown.connect(self._show_detail_room)
        self.values.place_requested.connect(self.structure.select)
        self.values.point_chosen.connect(self._point_chosen)

    def _point_chosen(self, asset_id: int) -> None:
        """New readings go to the chosen point's element, so they take that point."""
        if self.campaign_id is not None:
            self.place_targets[self.campaign_id] = asset_id or None
            self._show_place(asset_id or None)

    def _show_detail_room(self, chosen: bool, photos: int, run: str) -> None:
        """Sections without anything to show shrink to a line that says why."""
        if run:
            self.detail_section.set_empty(f"„{run}“ hat mehrere Schritte. Ein Klick auf die"
                                          " Zeit klappt sie auf, dann lässt sich jeder einzeln"
                                          " bearbeiten.")
        else:
            self.detail_section.set_empty(None if chosen else "Eine Zeile der Tabelle wählen.")
        if photos:
            self.photo_section.set_empty(None)
        elif chosen:
            self.photo_section.set_empty("Keine Fotos zu dieser Messung. Fotos auf die Zeile"
                                         " ziehen oder per Rechtsklick anhängen.")
        else:
            self.photo_section.set_empty("Zeigt die Fotos der gewählten Messung.")

    def _row_takes_photo(self, position) -> bool:
        campaign = self._campaign()
        open_campaign = bool(campaign) and campaign["status"] == "open"
        index = self.values.table.indexAt(position)
        # A line for a whole run is no single measurement a photo could belong to.
        return (open_campaign and index.isValid()
                and self.values.table.item(index.row(), 0).data(ROW_ID) is not None)

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
        self.header.assign_button.setVisible(placed)
        self.header.assign_button.setChecked(self.timeline.isVisibleTo(self))
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
