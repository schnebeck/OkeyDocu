# OkeyDocu - okeydocu/ui/repeat_compare.py
# Under a measurement of a repeat inspection: last time's values and what ran otherwise.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from ..l10n import tr
from .common import AppContext
from .guided_pages import ReasonOverlay


def _label(dim: bool = False) -> QLabel:
    label = QLabel()
    label.setWordWrap(True)
    label.setEnabled(not dim)
    return label


class RepeatCompare(QWidget):
    """Under a measurement that took a point: last time's values, and what ran otherwise."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.step_row = None
        self.before = _label(True)
        self.notable = _label()
        self.notable.setStyleSheet("color: #c27c0e;")
        self.deviation = _label()
        self.deviation.setStyleSheet("color: #c0392b;")
        self.reason = _label(True)
        self.reason_button = QPushButton(tr("Justify deviation …"))
        self.reason_button.clicked.connect(self._give_reason)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 0)
        for widget in (self.before, self.notable, self.deviation, self.reason):
            layout.addWidget(widget)
        layout.addWidget(self.reason_button, 0, Qt.AlignmentFlag.AlignRight)

    def show_measurement(self, row) -> None:
        """Shown only for a measurement that took a point of a repeat inspection."""
        step_row = None
        if row is not None and row["step_id"] is not None:
            step_row = self.app.db.one("SELECT * FROM steps WHERE id=?", row["step_id"])
        step = self.app.service.plan_step(step_row) if step_row else None
        self.step_row = step_row
        took_point = bool(step and step.origin)
        self.setVisible(took_point)
        if not took_point:
            return
        line, notable = self.app.service.comparison(step, row["id"])
        deviations = self.app.service.deviations(step, row["id"])
        self.before.setText(line)
        self.notable.setText("  ·  ".join(notable))
        self.deviation.setText(
            tr("Unlike last time:  {deviations}", deviations="  ·  ".join(deviations))
            if deviations else ""
        )
        self.reason.setText(tr("Reason: {note}", note=step_row["note"]) if step_row["note"] else "")
        open_campaign = self.app.service.campaign(row["campaign_id"])["status"] == "open"
        for widget, text in ((self.before, line), (self.notable, notable),
                             (self.deviation, deviations), (self.reason, step_row["note"])):
            widget.setVisible(bool(text))
        self.reason_button.setVisible(bool(deviations) and not step_row["note"] and open_campaign)

    def _give_reason(self) -> None:
        overlay = ReasonOverlay(self, tr("Justify deviation"))
        overlay.ok_button.setText(tr("Justify"))
        if overlay.exec():
            self.app.service.accept_deviation(self.step_row["id"],
                                              overlay.reason.toPlainText().strip())
            self.changed.emit()
