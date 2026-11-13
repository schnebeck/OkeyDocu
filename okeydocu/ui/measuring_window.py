# OkeyDocu - okeydocu/ui/measuring_window.py
# The window of a guided first measurement: stations on top, the scene left, the step right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""No station can be skipped, but each can be left at once: "Next" does not wait for the
instrument, the tester confirms by going on. Leaving the installation station stores what was
entered at the element and draws the bench from it; entering the leads station lays the
leads."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from ..campaign.measuring_place import candidates, measuring_place
from ..devices import driver_info
from ..devices.guide import LEADS, PLACE, STATIONS
from ..l10n import tr
from .bench_view import BenchView
from .place_form import PlaceForm
from .place_scene import PlaceScene

DONE = "background:#2e8b57;color:white"
NOW = "background:#ff9f1c;color:#1f2933;font-weight:bold"
LATER = "background:#d5dadf;color:#555"
CAUTION = "#b03a2e"


class MeasuringWindow(QDialog):
    def __init__(self, app, campaign_id: int, driver: str, function: str,
                 asset_id: int | None, parent=None):
        super().__init__(parent)
        info = driver_info(driver)
        self.app = app
        self.guide = info.guide(function)
        self.root = app.service.campaign(campaign_id)["asset_id"]
        self.station = 0
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
        self.step_text = QLabel()
        self.step_text.setWordWrap(True)
        self.step_text.setTextFormat(Qt.TextFormat.RichText)
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
        self.place = measuring_place(self.app.service, self.guide, asset_id, self.root)
        self.scene.show_place(self.guide, self.place)
        self.form.show_place(self.guide, self.place,
                             candidates(self.app.service, self.guide, self.root))
        self.bench.show_guide(self.guide, self.place.lines(), self.place.poles,
                              self.place.n_left)
        where = self.place.title or tr("no element chosen")
        self.head.setText(f"<b style='font-size:15pt'>{escape(tr(self.guide.title))}</b>"
                          f"&nbsp;&nbsp;<span style='color:gray'>"
                          f"{escape(tr('for {element}', element=where))}"
                          f" · {escape(tr('first measurement'))}</span>")

    def go(self, station: int) -> None:
        if station >= len(STATIONS):
            self.accept()
            return
        if self.station == PLACE and station > PLACE and self.form.store():
            self.show_place(self.place.asset_id)
        if self.station == LEADS and station != LEADS:
            self.bench.finish()
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
        if self.station == LEADS:
            self.next.setText(tr("Connected – next ▶"))
            self.bench.lay_leads()

    def _station_text(self) -> str:
        if self.station != LEADS:
            return f"<i>{escape(tr('This station follows.'))}</i>"
        steps = "".join(f"<li>{escape(tr(lead.text))}</li>" for lead in self.guide.leads)
        plugs = ", ".join(lead.plug for lead in sorted(self.guide.leads, key=lambda l: l.plug))
        caution = (f"<p style='color:{CAUTION}'>⚠ {escape(tr(self.guide.caution))}</p>"
                   if self.guide.caution else "")
        plugged = tr("Leads {plugs} are plugged into their rows of sockets.", plugs=plugs)
        return f"<p>{escape(plugged)}</p><ol>{steps}</ol>{caution}"
