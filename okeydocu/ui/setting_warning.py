# OkeyDocu - okeydocu/ui/setting_warning.py
# RCD tests that do not match their RCD: a warning window when a reading arrives, orange rows.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The report states the settings as they were and judges nothing about them; the app shows
a finding as long as it exists, so correcting the element's data or the place a reading is
booked on takes the mark away."""

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QMessageBox, QTableWidget

from ..campaign.setting_check import SettingCheck
from ..l10n import plural, tr

# Translucent, so it reads on a light and on a dark table alike.
ORANGE = QColor(245, 140, 20, 70)


def tip(found: list) -> str:
    lines = [tr("Instrument settings to check:")]
    return "\n".join(lines + [f"• {finding.text()}" for finding in found])


def warnings_of(db, rows) -> dict[int, str]:
    """For each stored measurement with a finding, by id, what it is."""
    check = SettingCheck(db)
    found = {row["id"]: check.of_row(row) for row in rows}
    return {key: tip(value) for key, value in found.items() if value}


def differing(db, campaign_id: int) -> list:
    """The measurements of a campaign with a finding, as measured."""
    rows = db.query("SELECT * FROM measurements WHERE campaign_id=? ORDER BY local_time, id",
                    campaign_id)
    found = warnings_of(db, rows)
    return [row for row in rows if row["id"] in found]


def campaign_note(db, campaign_id: int) -> str:
    """After an import: how many measurements of the campaign have a finding."""
    count = len(differing(db, campaign_id))
    if not count:
        return ""
    return "⚠ " + plural(count, "{count} RCD test does not match its RCD; it is marked orange.",
                         "{count} RCD tests do not match their RCD; they are marked orange.")


def mark_row(table: QTableWidget, index: int, text: str) -> None:
    for column in range(table.columnCount()):
        item = table.item(index, column)
        if item is not None:
            item.setBackground(ORANGE)
            item.setToolTip(text)


class SettingsWarning(QMessageBox):
    """A window of its own over the campaign; readings go on arriving while it is open."""

    def __init__(self, found: list, parent=None):
        super().__init__(QMessageBox.Icon.Warning, tr("Check the instrument settings"), "",
                         QMessageBox.StandardButton.Ok, parent)
        items = "".join(f"<li>{escape(finding.text())}</li>" for finding in found)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setText(f"<b>{escape(tr('The reading is stored, but it does not match its RCD:'))}"
                     f"</b><ul>{items}</ul>")
        self.setInformativeText(tr("Before the next measurement, correct the instrument, the"
                                   " RCD's data or the place the reading is booked on."))
        self.button(QMessageBox.StandardButton.Ok).setText(tr("Understood"))
