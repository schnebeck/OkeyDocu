# OkeyDocu - okeydocu/ui/measuring_window.py
# The window of a guided measurement: stations on top, the scene left, the step right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The stations are the driver's flow for the measurement, in its order. No station can be
skipped, but each can be left at once: "Next" does not wait for the instrument, the tester
confirms by going on. The leads stay laid once they are. The measure station waits for the
result; once it is there, "Done" ends the guide. A repeat measurement passes by what stays as
it was (see repeat_run). The button that goes on keeps one width whatever it says, so it stays
where the hand expects it. An instrument without a drawing of its panel shows the test point
instead of the bench."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, \
    QStackedWidget, QVBoxLayout

from ..devices import driver_info
from ..devices.guide import CONFIGURE, CONNECT, PLACE, SELECT
from ..l10n import N_, tr
from .bench_view import BenchView
from .button_width import widest
from .dial_station import POLL_MS, DialStation
from .footer_bar import FooterBar
from .guide_run import GuideRun
from .place_form import PlaceForm
from .place_scene import PlaceScene
from .place_station import PlaceStation
from .repeat_run import RepeatRun
from .station_bar import StationBar
from .station_kinds import StationKinds


RIGHT, GAP = 1, 2  # rows of the side column: what the station shows, and the room below
NEXT_TEXTS = (N_("Prepared – next ▶"), N_("Turned – next ▶"), N_("Connected – next ▶"),
              N_("Set – next ▶"), N_("Next ▶"), N_("Done ▶"))


class Absent:
    """Stands for the bench of an instrument without a panel drawing: whatever is asked of it
    does nothing."""

    def __getattr__(self, _name):
        return self

    def __call__(self, *args, **kwargs):
        return self

    def __bool__(self) -> bool:
        return False


class MeasuringWindow(PlaceStation, DialStation, StationKinds, RepeatRun, GuideRun, QDialog):
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
        self.flow = self.guide.flow
        self.owners = (self.guide,) * len(self.flow)  # the guide each station belongs to
        self.index = 0
        self.position = None  # the dial position the instrument reported last
        self.readings: dict[str, object] = {}  # by the function of the guide a result ends
        self._recall_leads(campaign_id)
        self.setWindowTitle(tr(self.guide.title))
        self.resize(1440, 1020)
        self.head = QLabel()
        self.bar = StationBar(tuple(station.heading() for station in self.flow))
        self.scene = PlaceScene()
        self.bench = BenchView(info.panel) if info.panel is not None else Absent()
        self.softkeys = info.panel.softkeys if info.panel is not None else ()
        self.left = QStackedWidget()
        self.left.addWidget(self.scene)
        if self.bench:
            self.left.addWidget(self.bench)
        self.form = PlaceForm(app)
        self.form.show_root(self.root, campaign_id)
        self.form.chosen.connect(self._choose)
        self.form.changed.connect(
            lambda: self._choose(self.form.panel.tree.current_id()))
        self.form.edited.connect(self._preview)
        self.step_text = QLabel()
        self.step_text.setWordWrap(True)
        self.step_text.setTextFormat(Qt.TextFormat.RichText)
        self.step_text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.right = QStackedWidget()
        self.right.addWidget(self.form)
        self.right.addWidget(self.step_text)
        self.step_title = QLabel()
        self.poll = QTimer(self, interval=POLL_MS)
        self.poll.timeout.connect(self._poll_selector)
        self.back = QPushButton(tr("◀ Back"))
        self.next = QPushButton()
        self.next.setDefault(True)
        self.next.setFixedWidth(widest(self.next, [tr(text) for text in NEXT_TEXTS]))
        self.back.clicked.connect(lambda: self.go(self.index - 1))
        self.next.clicked.connect(lambda: self.go(self.index + 1))
        self._lay_out()
        self.show_place(asset_id)
        self.go(0)

    def _lay_out(self) -> None:
        side = QFrame()
        side.setFrameShape(QFrame.Shape.StyledPanel)
        side.setMinimumWidth(360)
        column = self.column = QVBoxLayout(side)
        column.addWidget(self.step_title)
        column.addWidget(self.right)
        column.addStretch(1)
        self.footer = FooterBar()
        self.footer.add_leading(self.back)
        self.footer.add(self.next)
        column.addWidget(self.footer)
        body = QHBoxLayout()
        body.addWidget(self.left, 3)
        body.addWidget(side, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.head)
        layout.addWidget(self.bar)
        layout.addLayout(body, 1)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.poll.start()

    def hideEvent(self, event) -> None:
        self.poll.stop()
        super().hideEvent(event)

    @property
    def count(self) -> int:
        """How many stations this run has."""
        return len(self.flow)

    @property
    def kind(self) -> str:
        return self.flow[self.index].kind

    @property
    def has_dial(self) -> bool:
        return bool(self.bench) and self.guide.selector is not None

    def go_to(self, kind: str) -> None:
        """To the first station of a kind in this run."""
        self.go([station.kind for station in self.flow].index(kind))

    def _allow_next(self) -> None:
        """The first station is left only with an element the readings go to."""
        self.next.setEnabled(self.kind != PLACE or self.has_place)

    def go(self, index: int) -> None:
        if index >= self.count:
            if self.kind == PLACE:
                self._keep_place()
            self.accept()
            return
        forward = index > self.index
        if self.kind == PLACE and forward:
            self._keep_place()
        if self.kind == CONNECT and forward:
            self.bench.finish()
        self.index = self._past_passed(max(index, 0), 1 if forward else -1)
        self._take_guide()
        if self._leads_passed():
            self.bench.finish()
        station = self.flow[self.index]
        self.bar.show_station(self.index, self.count)
        self.step_title.setText(f"<b style='font-size:13pt'>{self.index + 1} · "
                                f"{escape(tr(station.heading()))}</b>")
        here = self.kind == PLACE or not self.bench
        self.left.setCurrentWidget(self.scene if here else self.bench)
        self.right.setCurrentWidget(self.form if self.kind == PLACE else self.step_text)
        self.column.setStretch(RIGHT, int(self.kind == PLACE))  # the tree takes what is left
        self.column.setStretch(GAP, int(self.kind != PLACE))
        self.back.setEnabled(self.index > 0)
        self.bench.panel.zoom_dial(self.kind == SELECT and self.has_dial)
        self.bench.leads_layer.setVisible(self.kind != CONFIGURE)  # no room in a close view
        self._on_display()
        last = self.index == self.count - 1
        self.next.setText(tr("Done ▶") if last else tr("Next ▶"))
        self._allow_next()
        getattr(self, f"_enter_{station.kind}")(station)
