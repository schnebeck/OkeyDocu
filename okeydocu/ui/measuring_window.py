# OkeyDocu - okeydocu/ui/measuring_window.py
# The window of a guided first measurement: stations on top, the scene left, the step right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""No station can be skipped, but each can be left at once: "Next" does not wait for the
instrument, the tester confirms by going on. Leaving the installation station stores what was
entered at the element, making it first where it is new, and draws the bench from it. The
dial station turns the knob to the position wanted and goes on by itself, a moment after the
instrument reports a position that serves the measurement; entering the leads station lays
the leads."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from ..campaign.measuring_place import (
    candidates,
    make_place,
    measuring_place,
    new_place,
    places,
)
from ..devices import driver_info
from ..devices.guide import DIAL, LEADS, PLACE, STATIONS
from ..l10n import tr
from .bench_view import BenchView
from .place_form import NEW, PlaceForm
from .place_scene import PlaceScene
from .station_texts import dial_text, fits, later_text, leads_text

DONE = "background:#2e8b57;color:white"
NOW = "background:#ff9f1c;color:#1f2933;font-weight:bold"
LATER = "background:#d5dadf;color:#555"
AUTO_MS = 900  # a right dial position is shown that long before the guide goes on


class MeasuringWindow(QDialog):
    place_made = Signal(int)  # an element made on the way, readings now go there
    parent_chosen = Signal(int)  # where new elements hang, kept until changed

    def __init__(self, app, campaign_id: int, driver: str, function: str,
                 asset_id: int | None, new_parent: int | None = None, parent=None):
        super().__init__(parent)
        info = driver_info(driver)
        self.app = app
        self.guide = info.guide(function)
        self.root = app.service.campaign(campaign_id)["asset_id"]
        self.parent_id = next((place for place in (new_parent, asset_id)
                               if place is not None), self.root)
        self.station = 0
        self.position = None  # the dial position the instrument reported last
        self.setWindowTitle(tr(self.guide.title))
        self.resize(1440, 1020)
        self.head = QLabel()
        self.chips = [QLabel() for _ in STATIONS]
        bar = QHBoxLayout()
        for chip in self.chips:
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bar.addWidget(chip)
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
        self.back = QPushButton(tr("◀ Back"))
        self.next = QPushButton()
        self.next.setDefault(True)
        self.back.clicked.connect(lambda: self.go(self.station - 1))
        self.next.clicked.connect(lambda: self.go(self.station + 1))
        self._lay_out(bar)
        self.show_place(asset_id)
        self.go(0)

    def _lay_out(self, bar: QHBoxLayout) -> None:
        side = QFrame()
        side.setFrameShape(QFrame.Shape.StyledPanel)
        side.setMinimumWidth(360)
        column = QVBoxLayout(side)
        column.addWidget(self.step_title)
        column.addWidget(self.right)
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
        layout.addLayout(bar)
        layout.addLayout(body, 1)

    def show_place(self, asset_id: int | None) -> None:
        service = self.app.service
        found = None if asset_id == NEW else measuring_place(service, self.guide, asset_id,
                                                              self.root)
        if found is None or found.asset_id is None:
            found = new_place(service, self.guide, self.parent_id, self.root)
        self.place = found
        self.form.show_place(self.guide, self.place, candidates(service, self.guide, self.root),
                             places(service, self.root), self.parent_id)
        self._preview()

    def _hang_below(self, parent_id: int) -> None:
        """A new element hangs below another one; what was entered stays."""
        self.parent_id = parent_id
        moved = new_place(self.app.service, self.guide, parent_id, self.root)
        self.place = moved.entered(self.place.features)
        self._preview()
        self.parent_chosen.emit(parent_id)

    def _shown(self):
        """The place as entered so far, a new one under a name of its own."""
        if not self.place.is_new:
            return self.place.entered(self.form.entered())
        return self.place.entered(self.form.entered(),
                                  tr("{title} (new)", title=self.form.title()))

    def _preview(self) -> None:
        shown = self._shown()
        self.scene.show_place(self.guide, shown)
        self.bench.show_guide(self.guide, shown.lines(), shown.poles, shown.n_left)
        where = shown.title or tr("no element chosen")
        self.head.setText(f"<b style='font-size:15pt'>{escape(tr(self.guide.title))}</b>"
                          f"&nbsp;&nbsp;<span style='color:gray'>"
                          f"{escape(tr('for {element}', element=where))}"
                          f" · {escape(tr('first measurement'))}</span>")

    def _keep_place(self) -> None:
        if self.place.is_new:
            made = self.place.entered(self.form.entered())
            name = self.form.name.text().strip() or self.form.name.placeholderText()
            asset_id = make_place(self.app.service, made, self.parent_id, name,
                                  self.form.identifier.text().strip())
            self.show_place(asset_id)
            self.place_made.emit(asset_id)
        elif self.form.store():
            self.show_place(self.place.asset_id)

    def go(self, station: int) -> None:
        if station >= len(STATIONS):
            self.accept()
            return
        if self.station == PLACE and station > PLACE:
            self._keep_place()
        if self.station == LEADS and station != LEADS:
            self.bench.finish()
        self.bench.panel.zoom_dial(station == DIAL)
        self.station = max(station, 0)
        for index, (chip, name) in enumerate(zip(self.chips, STATIONS)):
            state = DONE if index < self.station else NOW if index == self.station else LATER
            mark = "✓" if index < self.station else str(index + 1)
            chip.setText(f"{mark}  {tr(name)}")
            chip.setStyleSheet(state + ";border-radius:12px;padding:6px 10px")
        self.step_title.setText(f"<b style='font-size:13pt'>{self.station + 1} · "
                                f"{escape(tr(STATIONS[self.station]))}</b>")
        self.left.setCurrentWidget(self.scene if self.station == PLACE else self.bench)
        self.right.setCurrentWidget(self.form if self.station == PLACE else self.step_text)
        self.step_text.setText(self._station_text())
        self.back.setEnabled(self.station > 0)
        last = self.station == len(STATIONS) - 1
        self.next.setText(tr("Done ▶") if last else tr("Next ▶"))
        if self.station == PLACE:
            self.next.setText(tr("Prepared – next ▶"))
        if self.station == DIAL:
            self.next.setText(tr("Turned – next ▶"))
            self.bench.clear_leads()
            self.bench.panel.point_at(f"pos-{self.guide.selector}")
            self._show_dial()
        if self.station == LEADS:
            self.next.setText(tr("Connected – next ▶"))
            self.bench.lay_leads()

    def show_selector(self, position) -> None:
        """A dial position read from the instrument."""
        self.position = position
        if self.station == DIAL:
            self._show_dial()

    def _show_dial(self) -> None:
        right = fits(self.guide, self.position)
        value = self.position.value if self.position is not None else None
        self.bench.panel.show_actual(value, right if self.position is not None else None)
        self.step_text.setText(dial_text(self.guide, self.position))
        if right:
            QTimer.singleShot(AUTO_MS, self._dial_done)

    def _dial_done(self) -> None:
        if self.station == DIAL and fits(self.guide, self.position):
            self.go(DIAL + 1)

    def _station_text(self) -> str:
        return leads_text(self.guide) if self.station == LEADS else later_text()
