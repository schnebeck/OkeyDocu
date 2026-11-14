# OkeyDocu - okeydocu/ui/measuring_window.py
# The window of a guided measurement: stations on top, the scene left, the step right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""No station can be skipped, but each can be left at once: "Next" does not wait for the
instrument, the tester confirms by going on. The leads stay laid once they are, through
supply, settings and measuring. The last station waits for the result; once it is there,
"Done" ends the guide. A repeat measurement only has the first station: the element the
readings go to, chosen or made on the way."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, \
    QStackedWidget, QVBoxLayout

from ..campaign.line_conductors import LINE_CONDUCTORS
from ..devices import driver_info
from ..devices.guide import DIAL, LEADS, MEASURE, MODE, PLACE, STATIONS, SUPPLY
from ..l10n import tr
from ..vocabulary import setting_name
from .bench_view import BenchView
from .dial_station import DialStation
from .place_form import PlaceForm
from .place_scene import PlaceScene
from .place_station import PlaceStation
from .station_bar import StationBar
from .station_texts import conductors_text, leads_text, measure_text, mode_text, \
    supply_text


class MeasuringWindow(PlaceStation, DialStation, QDialog):
    place_made = Signal(int)  # an element made on the way
    place_kept = Signal(int)  # the element readings now go to, made on the way or chosen
    parent_chosen = Signal(int)  # where new elements hang, kept until changed
    selector_wanted = Signal()  # the guide would like to know where the switch stands

    def __init__(self, app, campaign_id: int, driver: str, function: str,
                 asset_id: int | None, new_parent: int | None = None, parent=None,
                 repeat: bool = False):
        super().__init__(parent)
        info = driver_info(driver)
        self.app = app
        self.base_guide = self.guide = info.guide(function)
        self.repeat = repeat
        self.root = app.service.campaign(campaign_id)["asset_id"]
        self.parent_id = next((place for place in (new_parent, asset_id)
                               if place is not None), self.root)
        self.station = 0
        self.position = None  # the dial position the instrument reported last
        self.reading = None  # the result the last station waits for
        self.setWindowTitle(tr(self.guide.title))
        self.resize(1440, 1020)
        self.head = QLabel()
        self.bar = StationBar(STATIONS)
        self.scene = PlaceScene()
        self.bench = BenchView(info.panel)
        self.left = QStackedWidget()
        self.left.addWidget(self.scene)
        self.left.addWidget(self.bench)
        self.form = PlaceForm(app)
        self.form.element_chosen.connect(self.show_place)
        self.form.edited.connect(self._preview)
        self.form.parent_chosen.connect(self._hang_below)
        self.step_text = QLabel()
        self.step_text.setWordWrap(True)
        self.step_text.setTextFormat(Qt.TextFormat.RichText)
        self.step_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.right = QStackedWidget()
        self.right.addWidget(self.form)
        self.right.addWidget(self.step_text)
        self.step_title = QLabel()
        self.ask = QPushButton(tr("Ask the instrument again"))
        self.ask.clicked.connect(self.selector_wanted)
        self.back = QPushButton(tr("◀ Back"))
        self.next = QPushButton()
        self.next.setDefault(True)
        self.back.clicked.connect(lambda: self.go(self.station - 1))
        self.next.clicked.connect(lambda: self.go(self.station + 1))
        self._lay_out()
        self.show_place(asset_id)
        self.go(0)

    def _lay_out(self) -> None:
        side = QFrame()
        side.setFrameShape(QFrame.Shape.StyledPanel)
        side.setMinimumWidth(360)
        column = QVBoxLayout(side)
        column.addWidget(self.step_title)
        column.addWidget(self.right)
        column.addWidget(self.ask)
        column.addStretch(1)
        nav = QHBoxLayout()
        nav.addWidget(self.back)
        nav.addStretch(1)
        nav.addWidget(self.next)
        column.addLayout(nav)
        body = QHBoxLayout()
        body.addWidget(self.left, 3)
        body.addWidget(side, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.head)
        layout.addWidget(self.bar)
        layout.addLayout(body, 1)

    @property
    def count(self) -> int:
        """How many stations this run has."""
        return 1 if self.repeat else len(STATIONS)

    def go(self, station: int) -> None:
        if station >= self.count:
            if self.station == PLACE:
                self._keep_place()
            self.accept()
            return
        if self.station == PLACE and station > PLACE:
            self._keep_place()
        if self.station == LEADS and station > LEADS:
            self.bench.finish()
        self.station = max(station, 0)
        self.bar.show_station(self.station, self.count)
        self.step_title.setText(f"<b style='font-size:13pt'>{self.station + 1} · "
                                f"{escape(tr(STATIONS[self.station]))}</b>")
        self.left.setCurrentWidget(self.scene if self.station == PLACE else self.bench)
        self.right.setCurrentWidget(self.form if self.station == PLACE else self.step_text)
        self.back.setEnabled(self.station > 0)
        self.ask.hide()
        self._enter(self.station)

    def _enter(self, station: int) -> None:
        panel = self.bench.panel
        panel.zoom_dial(station == DIAL)
        self.bench.leads_layer.setVisible(station != MODE)  # a close view has no room for them
        last = station == self.count - 1
        self.next.setText(tr("Done ▶") if last else tr("Next ▶"))
        if station == PLACE:
            self.next.setText(tr("Take it ▶") if self.repeat else tr("Prepared – next ▶"))
        elif station == DIAL:
            self.next.setText(tr("Turned – next ▶"))
            self._enter_dial()
        elif station == LEADS:
            self.next.setText(tr("Connected – next ▶"))
            self.step_text.setText(leads_text(self.guide))
            self.bench.lay_leads()
        elif station == SUPPLY:
            parts = ("mains-inlet", "mains-switch", "led-mains") if self.guide.mains \
                else ("lcd",)
            panel.point_at(*parts)
            self.step_text.setText(supply_text(self.guide))
        elif station == MODE:
            parts = [part for action in self.guide.settings for part in action.parts]
            panel.zoom_parts("lcd", *parts)
            panel.point_at(*parts)
            self.next.setText(tr("Set – next ▶"))
            advice = conductors_text(self.guide, self.place.stated(LINE_CONDUCTORS),
                                     self.place.has_n)
            self.step_text.setText(mode_text(self.guide, self._settings(), self.place.title,
                                             advice))
        elif station == MEASURE:
            panel.point_at(*(part for action in self.guide.steps for part in action.parts))
            self.step_text.setText(measure_text(self.guide, self.reading))

    def _settings(self) -> list[tuple[str, str]]:
        """What the element states that is set on the instrument for this measurement."""
        keys = self.guide.element_features if self.guide.owner_feature else ()
        return [(setting_name(key) or key, self.place.stated(key)) for key in keys
                if self.place.stated(key) and setting_name(key)]

    def show_reading(self, reading) -> None:
        """A result from the instrument; the one this measurement waits for ends it."""
        if not self.guide.ended_by(reading.measurement.function):
            return
        self.reading = reading
        if self.station == MEASURE:
            self.bench.panel.point_at()
            self.step_text.setText(measure_text(self.guide, reading))
