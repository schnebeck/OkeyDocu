# OkeyDocu - okeydocu/ui/measuring_window.py
# The window of a guided first measurement: stations on top, bench on the left, the step right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""No station can be skipped, but each can be left at once: "Next" does not wait for the
instrument, the tester confirms by going on. Entering the test leads station lays the leads."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from ..devices import driver_info
from ..devices.guide import LEADS, STATIONS
from ..l10n import tr

DONE = "background:#2e8b57;color:white"
NOW = "background:#ff9f1c;color:#1f2933;font-weight:bold"
LATER = "background:#d5dadf;color:#555"
CAUTION = "#b03a2e"


class MeasuringWindow(QDialog):
    def __init__(self, driver: str, function: str, element: str, data: list[str],
                 poles: int = 2, n_left: bool = False, parent=None):
        super().__init__(parent)
        from .bench_view import BenchView

        info = driver_info(driver)
        guide = info.guide(function)
        self.guide = guide
        self.station = 0
        self.setWindowTitle(tr(guide.title))
        self.resize(1440, 1020)
        head = QLabel(f"<b style='font-size:15pt'>{escape(tr(guide.title))}</b>&nbsp;&nbsp;"
                      f"<span style='color:gray'>{escape(tr('for {element}', element=element))}"
                      f" · {escape(tr('first measurement'))}</span>")
        self.chips = [QLabel() for _ in STATIONS]
        bar = QHBoxLayout()
        for chip in self.chips:
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            bar.addWidget(chip)
        self.bench = BenchView(info.panel)
        self.bench.show_guide(guide, data, poles, n_left)
        self.step_title = QLabel()
        self.step_text = QLabel()
        self.step_text.setWordWrap(True)
        self.step_text.setTextFormat(Qt.TextFormat.RichText)
        self.back = QPushButton(tr("◀ Back"))
        self.next = QPushButton()
        self.next.setDefault(True)
        self.back.clicked.connect(lambda: self.go(self.station - 1))
        self.next.clicked.connect(lambda: self.go(self.station + 1))
        side = QFrame()
        side.setFrameShape(QFrame.Shape.StyledPanel)
        side.setMinimumWidth(340)
        column = QVBoxLayout(side)
        column.addWidget(self.step_title)
        column.addWidget(self.step_text)
        column.addStretch(1)
        nav = QHBoxLayout()
        nav.addWidget(self.back)
        nav.addStretch(1)
        nav.addWidget(self.next)
        column.addLayout(nav)
        body = QHBoxLayout()
        body.addWidget(self.bench, 3)
        body.addWidget(side, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(head)
        layout.addLayout(bar)
        layout.addLayout(body, 1)
        self.go(0)

    def go(self, station: int) -> None:
        if station >= len(STATIONS):
            self.accept()
            return
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
        self.step_text.setText(self._station_text())
        self.back.setEnabled(self.station > 0)
        last = self.station == len(STATIONS) - 1
        self.next.setText(tr("Done ▶") if last else tr("Next ▶"))
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
