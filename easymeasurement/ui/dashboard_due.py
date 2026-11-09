# EasyMeasurement - easymeasurement/ui/dashboard_due.py
# On the start screen: inspections that are due again and defects waiting for a follow-up.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date
from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .campaign_list import heading
from .common import AppContext
from .dashboard_card import ALERT, CARD_STYLE, TODO
from .kind_catalog import KindCatalog

SHOWN = 5


def _since(due: date, today: date) -> str:
    days = (today - due).days
    if days < 0:
        return f"fällig am {due:%d.%m.%Y}, in {-days} Tagen"
    if days == 0:
        return "heute fällig"
    weeks = days // 7
    return f"seit {due:%d.%m.%Y} fällig" + (f", {weeks} Wochen über" if weeks > 1 else "")


class DueRow(QFrame):
    """One thing to do, said in a line, with the button that starts it."""

    def __init__(self, icon, title: str, detail: str, colour: str, button_text: str, action):
        super().__init__(objectName="card")
        self.setStyleSheet(CARD_STYLE)
        picture = QLabel()
        picture.setPixmap(icon.pixmap(28, 28))
        text = QLabel(f"<b>{escape(title)}</b><br><span style='color:{colour}'>"
                      f"{escape(detail)}</span>")
        text.setTextFormat(Qt.TextFormat.RichText)
        text.setWordWrap(True)
        self.button = QPushButton(button_text)
        self.button.clicked.connect(action)
        row = QHBoxLayout(self)
        row.setContentsMargins(10, 6, 10, 6)
        row.addWidget(picture)
        row.addWidget(text, 1)
        row.addWidget(self.button)


class DueSection(QWidget):
    """Hidden while nothing is due; the most urgent comes first."""

    # asset, suggested title, campaign followed up (0 for none)
    start_requested = Signal(int, str, int)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.title = heading("Fällig", 13)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(6)
        self.more = QLabel()
        self.more.setEnabled(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title)
        layout.addLayout(self.rows)
        layout.addWidget(self.more)

    def refresh(self, today: date | None = None) -> None:
        today = today or date.today()
        while self.rows.count():
            widget = self.rows.takeAt(0).widget()
            widget.hide()
            widget.deleteLater()
        catalog = KindCatalog(self.app.db)
        rows = [self._follow_up(item, catalog) for item in self.app.service.open_follow_ups()]
        rows += [self._inspection(item, catalog, today)
                 for item in self.app.service.due_inspections(today)]
        for row in rows[:SHOWN]:
            self.rows.addWidget(row)
        self.more.setText(f"und {len(rows) - SHOWN} weitere" if len(rows) > SHOWN else "")
        self.more.setVisible(len(rows) > SHOWN)
        self.setVisible(bool(rows))

    def _inspection(self, item, catalog: KindCatalog, today: date) -> DueRow:
        title = f"Wiederholungsprüfung {item.due:%Y}"
        detail = (f"{_since(item.due, today)} · zuletzt geprüft am {item.last_day:%d.%m.%Y},"
                  f" alle {item.months} Monate")
        return DueRow(
            catalog.icon(item.kind), f"{item.asset} · {item.customer}", detail,
            ALERT if item.overdue(today) else TODO, "Prüfung anlegen …",
            lambda: self.start_requested.emit(item.asset_id, title, 0),
        )

    def _follow_up(self, item, catalog: KindCatalog) -> DueRow:
        defects = "1 Mangel" if item.failed == 1 else f"{item.failed} Mängel"
        detail = f"Nachprüfung offen: {defects} aus „{item.title}“ vom {item.closed:%d.%m.%Y}"
        return DueRow(
            catalog.icon(item.kind), f"{item.asset} · {item.customer}", detail, ALERT,
            "Nachprüfung anlegen …",
            lambda: self.start_requested.emit(item.asset_id, f"Nachprüfung: {item.title}",
                                              item.campaign_id),
        )
