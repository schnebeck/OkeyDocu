# EasyMeasurement - easymeasurement/ui/setting_warning.py
# Settings that differ from the element: a card when a reading arrives, orange rows after.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The report states the settings as they were and judges nothing about them; the app shows
the difference as long as it exists, so correcting the element's data takes the mark away."""

from __future__ import annotations

from html import escape

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QTableWidget

from ..campaign.setting_check import Mismatch, SettingCheck
from ..l10n import plural, tr
from .overlay import Overlay

# Translucent, so it reads on a light and on a dark table alike.
ORANGE = QColor(245, 140, 20, 70)


def tip(found: list[Mismatch]) -> str:
    lines = [tr("The instrument was set differently from the element:")]
    return "\n".join(lines + [f"• {mismatch.text()}" for mismatch in found])


def warnings_of(db, rows) -> dict[int, str]:
    """For each stored measurement whose settings differ, by id, what differs."""
    check = SettingCheck(db)
    found = {row["id"]: check.of_row(row) for row in rows}
    return {key: tip(value) for key, value in found.items() if value}


def differing(db, campaign_id: int) -> list:
    """The measurements of a campaign set differently from their element, as measured."""
    rows = db.query("SELECT * FROM measurements WHERE campaign_id=? ORDER BY local_time, id",
                    campaign_id)
    found = warnings_of(db, rows)
    return [row for row in rows if row["id"] in found]


def campaign_note(db, campaign_id: int) -> str:
    """After an import: how many measurements of the campaign were set differently."""
    count = len(differing(db, campaign_id))
    if not count:
        return ""
    return "⚠ " + plural(count, "{count} measurement was set differently from its element;"
                         " it is marked orange.", "{count} measurements were set differently"
                         " from their element; they are marked orange.")


def mark_row(table: QTableWidget, index: int, text: str) -> None:
    for column in range(table.columnCount()):
        item = table.item(index, column)
        if item is not None:
            item.setBackground(ORANGE)
            item.setToolTip(text)


class SettingsWarning(Overlay):
    """Opened without waiting: readings go on arriving behind it."""

    def __init__(self, found: list[Mismatch], parent=None):
        super().__init__(tr("Instrument settings differ from the element"), parent)
        items = "".join(f"<li>{escape(mismatch.text())}</li>" for mismatch in found)
        text = QLabel(
            tr("The reading is stored. The instrument was set differently from what the"
               " element states:") + f"<ul>{items}</ul>"
            + tr("Check the setting on the instrument, or the element's data, before the next"
                 " measurement."))
        text.setWordWrap(True)
        self.body.addWidget(text)
        self.ok_button.setText(tr("Understood"))
        self.cancel_button.hide()

    def open(self) -> None:
        self._open()

    def _leave(self) -> None:
        if self._loop is None:
            self._close()
        else:
            super()._leave()
