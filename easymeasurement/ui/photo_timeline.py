# EasyMeasurement - easymeasurement/ui/photo_timeline.py
# Assign photos to measurements like clips in a video editor: two tracks on one time axis.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..store import CampaignClosed
from .common import AppContext, function_short, show_error
from .photo_overlays import TimelineAsking
from .photo_shared import shared_thumbs
from .photo_timeline_data import TimelineData
from .photo_timeline_model import default_gap_seconds, shift_text
from .photo_timeline_scroll import TimelineScroll
from .photo_timeline_view import WIDEST_RATIO, TrackView

NO_TIME = "Dieses Foto hat keine Aufnahmezeit. Bitte auf eine Messung ziehen."
PICK_A_PHOTO = "Erst ein nicht angeheftetes Foto anklicken: die Lücke entsteht direkt davor."
CLOSED = "Die Kampagne ist abgeschlossen, Fotos lassen sich nicht mehr ändern."


class PhotoTimeline(TimelineAsking, QWidget):
    """The track of measurements above the track of photos. Hint line below."""

    changed = Signal()
    measurement_chosen = Signal(int)
    close_requested = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.campaign_id: int | None = None
        self.locked = False  # asked for by the window, on top of the campaign's own status
        self.closed = False
        self.rows: dict[int, object] = {}
        self.view = TrackView(shared_thumbs())
        self.view.describe = self._describe
        self.fit_button = self._button("Einpassen", "Alles in die Breite einpassen", self.view.fit)
        self.gap_button = self._button(
            "Lücke einfügen", "Vor dem gewählten Foto eine Lücke einfügen", self._gap_at_selection
        )
        self.start_button = self._button(
            "Start setzen …", "Die genaue Zeit des ersten Fotos eingeben", self._ask_start
        )
        self.scroll = TimelineScroll(self.view, WIDEST_RATIO)
        self.close_button = self._button("Schließen", "Die Zeitleiste ausblenden; „Fotos zuordnen“"
                                         " oben zeigt sie wieder", self.close_requested.emit)
        closing = self.style().standardIcon(QStyle.StandardPixmap.SP_TitleBarCloseButton)
        self.close_button.setIcon(QIcon.fromTheme("window-close", closing))
        self.close_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.shift_label = QLabel()
        self.hint_label = QLabel()
        self.hint_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 4, 0)
        for button in (self.fit_button, self.gap_button, self.start_button):
            bar.addWidget(button)
        bar.addStretch(1)
        bar.addWidget(self.shift_label)
        bar.addWidget(self.close_button)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(2)
        column.addLayout(bar)
        column.addWidget(self.view, 1)
        column.addWidget(self.scroll)
        column.addWidget(self.hint_label)
        view = self.view
        view.hint.connect(self.hint_label.setText)
        view.shift_moved.connect(self._show_shift)
        view.shift_done.connect(self._shift)
        view.pin_done.connect(self._pin)
        view.photo_returned.connect(self._carried_to_strip)
        view.gap_resized.connect(self._resize_gap)
        view.gap_closed.connect(lambda gap: self._write(self.app.service.remove_photo_gap, gap))
        view.mark_clicked.connect(self.measurement_chosen)
        view.photo_opened.connect(self.open_photo)
        view.delete_pressed.connect(self._stack_selected)
        view.menu_wanted.connect(self._open_menu)
        self.hint_label.setText(view.mouse.idle_hint())

    @staticmethod
    def _button(text: str, tip: str, action: Callable[[], None]) -> QToolButton:
        button = QToolButton(text=text, toolTip=tip, autoRaise=True)
        button.clicked.connect(lambda: action())
        return button

    # Public --------------------------------------------------------------

    def show_campaign(self, campaign_id: int) -> None:
        self.campaign_id = campaign_id
        self.view.selected = self.view.chosen_mark = None
        self.refresh()
        self.view.fit()

    def refresh(self) -> None:
        """Read everything again. The zoom stays, so the place of the work stays in view."""
        if self.campaign_id is None:
            return
        service = self.app.service
        campaign = service.campaign(self.campaign_id)
        measurements = service.measurements(self.campaign_id)
        self.rows = {row["id"]: row for row in measurements}
        data = TimelineData.from_rows(
            measurements, service.photos(self.campaign_id), service.photo_gaps(self.campaign_id),
            campaign["photo_shift_s"], function_short,
        )
        paths = {p.id: service.photo_path(self.campaign_id, p.file_name) for p in data.photos}
        self.closed = campaign["status"] != "open"
        self.view.show_data(data, paths)
        self._apply_lock()
        self._show_shift(data.shift)

    def set_read_only(self, read_only: bool) -> None:
        self.locked = read_only
        self._apply_lock()

    def select_measurement(self, measurement_id: int | None) -> None:
        """Show the links of a measurement chosen elsewhere, for example in the table."""
        self.view.choose_mark(measurement_id)

    @property
    def read_only(self) -> bool:
        return self.locked or self.closed

    def _apply_lock(self) -> None:
        self.view.set_read_only(self.read_only)
        self.gap_button.setEnabled(not self.read_only)
        self.start_button.setEnabled(not self.read_only)
        self.hint_label.setText(self.view.mouse.idle_hint())

    def _show_shift(self, seconds: float) -> None:
        self.shift_label.setText(shift_text(seconds))

    # Changing data --------------------------------------------------------

    def _write(self, work: Callable, *arguments) -> None:
        if self.read_only:
            return
        try:
            work(*arguments)
        except CampaignClosed:
            self.refresh()
            show_error(self, CLOSED)
            return
        self.refresh()
        self.changed.emit()

    def _shift(self, seconds: float) -> None:
        self._write(self.app.service.set_photo_shift, self.campaign_id, seconds)

    def _pin(self, photo_id: int, measurement_id: int) -> None:
        self._write(self.app.service.pin_photo, photo_id, measurement_id)

    def _carried_to_strip(self, photo_id: int) -> None:
        rows = self.app.service.photos(self.campaign_id)
        row = next((known for known in rows if known["id"] == photo_id), None)
        if row is None or not row["taken_at"]:
            self.hint_label.setText(NO_TIME)
        elif row["placement"] != "timeline":
            self._write(self.app.service.return_to_timeline, photo_id)

    def _add_gap(self, at: datetime) -> None:
        seconds = default_gap_seconds(self.view.axis.px_per_s)
        self._write(self.app.service.add_photo_gap, self.campaign_id, at, seconds)

    def _gap_at_selection(self) -> None:
        photo = self.view.data.photo(self.view.selected) if self.view.selected else None
        if photo is None or not photo.follows_time:
            self.hint_label.setText(PICK_A_PHOTO)
        else:
            self._add_gap(photo.taken)

    def _resize_gap(self, gap_id: int, seconds: float) -> None:
        self._write(self.app.service.resize_photo_gap, gap_id, seconds)

    def _stack_selected(self) -> None:
        if self.view.selected is not None:
            self._write(self.app.service.stack_photo, self.view.selected)
