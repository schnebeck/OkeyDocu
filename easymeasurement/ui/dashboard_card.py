# EasyMeasurement - easymeasurement/ui/dashboard_card.py
# One campaign on the start screen: where it stands and the next thing to do with it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from ..campaign.records import NO_INSTRUMENT
from ..campaign.service import CampaignSummary
from .campaign_list import count_text

CARD_STYLE = """
QFrame#card { background: palette(base); border: 1px solid palette(mid); border-radius: 6px; }
QFrame#card:hover { border: 1px solid palette(highlight); }
"""
CHIP_STYLE = "color: white; background: %s; border-radius: 3px; padding: 1px 6px;"
LIVE, ALERT = "#2e7d32", "#c62828"
TODO, READY = "#b26a00", "#2e7d32"
READY_TEXT = "Bereit zum Bestätigen"
CARD_WIDTH = 280

# What the button on a card does, sent with the campaign it belongs to.
SHOW, RESUME, OPEN_REPORT, MAKE_REPORT = "show", "resume", "open_report", "make_report"


def when_text(moment: datetime, today: date | None = None) -> str:
    today = today or date.today()
    if moment.date() == today:
        return f"heute {moment:%H:%M}"
    if moment.date() == today - timedelta(days=1):
        return f"gestern {moment:%H:%M}"
    return f"{moment:%d.%m.%Y}"


def attention(summary: CampaignSummary) -> list[str]:
    """What still has to happen before the campaign is done with."""
    if not summary.is_open:
        return [] if summary.reports else ["Noch kein Protokoll erstellt"]
    if summary.loose:
        return [f"{summary.loose} nicht zugeordnet"]
    # Open steps show in the progress bar.
    return [READY_TEXT] if summary.steps and summary.steps_done == summary.steps else []


def dim(label: QLabel) -> QLabel:
    """Secondary, yet readable: the text colour half way to the background."""
    palette = label.palette()
    text = palette.color(QPalette.ColorRole.WindowText)
    base = palette.color(QPalette.ColorRole.Base)
    mixed = QColor(*((a * 3 + b * 2) // 5 for a, b in zip(text.getRgb()[:3], base.getRgb()[:3])))
    palette.setColor(QPalette.ColorRole.WindowText, mixed)
    label.setPalette(palette)
    return label


def _label(text: str = "", secondary: bool = False) -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.PlainText)
    return dim(label) if secondary else label


class CampaignCard(QFrame):
    """A click anywhere shows the campaign; the button does the next step."""

    requested = Signal(str, int)

    def __init__(self, summary: CampaignSummary, live: bool = False, seal_warning: str = "",
                 icon=None):
        super().__init__(objectName="card")
        self.summary = summary
        self.live = live
        self.setStyleSheet(CARD_STYLE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(CARD_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setToolTip("Klicken, um die Kampagne anzusehen")
        state, colour = self._state(live, seal_warning)
        # A state worth a mark takes the place of the time.
        self.chip = QLabel(state)
        self.chip.setStyleSheet(CHIP_STYLE % colour)
        self.chip.setVisible(bool(state))
        self.when = _label(when_text(summary.active_at), secondary=True)
        self.when.setVisible(not state)
        self.title = _label(summary.title)
        font = self.title.font()
        font.setBold(True)
        font.setPointSize(font.pointSize() + 2)
        self.title.setFont(font)
        top = QHBoxLayout()
        top.addWidget(self.title, 1)
        top.addWidget(self.chip, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.when, 0, Qt.AlignmentFlag.AlignTop)
        place = summary.customer + (f", {summary.city}" if summary.city else "")
        self.place = _label(f"{place}  ·  {summary.asset}")
        self.picture = QLabel()
        if icon is not None:
            self.picture.setPixmap(icon.pixmap(18, 18))
        where = QHBoxLayout()
        where.setSpacing(6)
        where.addWidget(self.picture, 0, Qt.AlignmentFlag.AlignTop)
        where.addWidget(self.place, 1)
        plan = f"Messplan: {summary.plan_title}" if summary.plan_title else "Ohne Messplan"
        if summary.steps:
            plan += f"  ·  {summary.steps_done} von {summary.steps} Schritten"
        self.plan = _label(plan, secondary=True)
        self.progress = QProgressBar()
        self.progress.setRange(0, max(summary.steps, 1))
        self.progress.setValue(summary.steps_done)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(5)
        self.progress.setVisible(bool(summary.steps))
        self.figures = QLabel(self._figures())
        self.figures.setWordWrap(True)
        self.tester = _label(f"Prüfer: {summary.tester}" if summary.tester else "Prüfer fehlt",
                             secondary=True)
        self.button = QPushButton()
        self.button.clicked.connect(self._act)
        self.action = self._next_step()
        bottom = QHBoxLayout()
        bottom.addWidget(self.tester, 1)
        bottom.addWidget(self.button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        layout.addLayout(top)
        layout.addLayout(where)
        layout.addWidget(self.plan)
        layout.addWidget(self.progress)
        layout.addWidget(self.figures)
        layout.addStretch(1)
        layout.addLayout(bottom)

    def _state(self, live: bool, seal_warning: str) -> tuple[str, str]:
        if seal_warning:
            return seal_warning, ALERT
        if live:
            return "● Misst gerade", LIVE
        return "", ""

    def _figures(self) -> str:
        """Counts, failures in red, and what is still to do in amber."""
        parts = [count_text(self.summary.measured)]
        if self.summary.failed:
            parts.append(f'<span style="color:{ALERT}">{self.summary.failed} n. i. O.</span>')
        for point in attention(self.summary):
            colour = READY if point == READY_TEXT else TODO
            parts.append(f'<span style="color:{colour}">{escape(point)}</span>')
        return "  ·  ".join(parts)

    def _next_step(self) -> str:
        summary = self.summary
        if self.live:
            self.button.setText("Zur Messung")
            self.button.setToolTip("Die Kampagne zeigen, für die das Messgerät gerade misst")
            return SHOW
        if summary.is_open:
            measures = summary.driver not in NO_INSTRUMENT
            self.button.setText("Weitermessen" if measures else "Öffnen")
            self.button.setToolTip("Mit dem Messgerät verbinden und weitermachen" if measures
                                   else "Die Kampagne öffnen")
            return RESUME if measures else SHOW
        if summary.reports:
            self.button.setText("Protokoll öffnen")
            return OPEN_REPORT
        self.button.setText("Protokoll erstellen …")
        return MAKE_REPORT

    def _act(self) -> None:
        self.requested.emit(self.action, self.summary.id)

    def mouseReleaseEvent(self, event) -> None:
        inside = self.rect().contains(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and inside:
            self.requested.emit(SHOW, self.summary.id)
        super().mouseReleaseEvent(event)
