# EasyMeasurement - easymeasurement/ui/campaign_photos.py
# The photo timeline and stack of the campaign on screen, tied to its measurement table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from .common import ROW_ID, selected_id
from .photo_shared import accept_photo_drops
from .photo_stack import PhotoStack
from .photo_tabs import LOOSE
from .photo_timeline import PhotoTimeline
from .proxy_progress import ProxyProgress

WAIT_FOR_PROXIES = "Erst wenn die Fotos für das Protokoll vorbereitet sind (siehe Statuszeile)."
DRAFT_TIP = "Das Protokoll, wie es jetzt aussähe. Es ist noch nicht gültig."


class CampaignPhotos:
    """The timeline appears once a campaign has photos, so it never takes room for nothing."""

    def _build_photos(self) -> None:
        self.timeline = PhotoTimeline(self.app)
        self.timeline.hide()
        self.stack = PhotoStack(self.app)
        self.proxies = ProxyProgress(self)
        self.draft_open = False  # set with the campaign shown, so the timer needs no database
        self.proxy_note = QLabel()
        self.proxy_note.hide()
        self.proxies.changed.connect(self._proxies_changed)
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
        # The measurement's tab takes a photo for the chosen measurement, as its row does.
        self.tab_drops = [accept_photo_drops(
            target, self._dropped_on_measurement, allowed=lambda _: self._chosen_takes_photo(),
        ) for target in (self.photo_tabs.measurement_page, self.values.gallery.viewport())]
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
            self.photo_tabs.show_note(None)
        elif chosen:
            self.photo_tabs.show_note("Keine Fotos zu dieser Messung. Fotos auf die Zeile"
                                      " ziehen oder per Rechtsklick anhängen.")
        else:
            self.photo_tabs.show_note("Zeigt die Fotos der gewählten Messung.")
        self._quiet_photos()

    def _row_takes_photo(self, position) -> bool:
        campaign = self._campaign()
        open_campaign = bool(campaign) and campaign["status"] == "open"
        index = self.values.table.indexAt(position)
        # A line for a whole run is no single measurement a photo could belong to.
        return (open_campaign and index.isValid()
                and self.values.table.item(index.row(), 0).data(ROW_ID) is not None)

    def _chosen_takes_photo(self) -> bool:
        campaign = self._campaign()
        return (bool(campaign) and campaign["status"] == "open"
                and selected_id(self.values.table) is not None)

    def _dropped_on_measurement(self, photo_id: int, _position) -> None:
        self.app.service.pin_photo(photo_id, selected_id(self.values.table))
        self._photos_changed()

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
        self.warm_proxies(campaign_id)
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
        self.photo_tabs.set_loose(self.stack.count)
        self.photo_section.set_alert(self.stack.count > 0)
        self._quiet_photos()
        self._show_checks(self._campaign())

    def _refresh_photos(self) -> None:
        """After a change of the measurements, which the timeline shows as well."""
        if self.campaign_id is not None:
            self.timeline.refresh()
            self.stack.refresh()
            self._fit_photo_panels()

    def show_stack(self) -> None:
        """Opens the tab of the photos of no measurement and brings it into view."""
        action = getattr(self.window(), "side_action", None)  # keeps the menu in step
        action.setChecked(True) if action is not None else self.side.show()
        self.photo_section.toggle.setChecked(True)
        self.photo_tabs.setCurrentIndex(LOOSE)
        self.side.ensureWidgetVisible(self.photo_section)

    def _quiet_photos(self) -> None:
        """Without any photo to show, the section keeps small."""
        self.photo_section.set_quiet(self.photo_tabs.gallery.isHidden() and not self.stack.count)

    def _photos_changed(self) -> None:
        self.guided.reload()
        self._data_changed()

    def warm_proxies(self, campaign_id: int) -> None:
        """Reduced copies for thumbnails and the report, made beside the window."""
        self.proxies.follow(campaign_id, self.app.service.warm_proxies(campaign_id))
        self._proxies_changed()

    def _proxies_changed(self) -> None:
        """The draft waits for the proxies, so it never shows a half-prepared report."""
        text = self.proxies.text()
        self.proxy_note.setText(text)
        self.proxy_note.setVisible(bool(text))
        ready = self.proxies.ready(self.campaign_id)
        usable = self.draft_open and ready
        self.draft_action.setEnabled(usable)
        self.header.draft_button.setEnabled(usable)
        self.header.draft_button.setToolTip(DRAFT_TIP if ready else WAIT_FOR_PROXIES)
