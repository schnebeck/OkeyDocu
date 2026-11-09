# EasyMeasurement - easymeasurement/ui/measurement_editing.py
# What the field beside the table holds back until it is taken over, and taking it over.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..campaign.service import TEXT_FIELDS
from ..store import CampaignClosed
from .common import show_error

FIELD_NAMES = {"function": "Messfunktion", "operator": "Prüfer", "verdict": "Bewertung",
               "lower_limit": "Grenzwert", "upper_limit": "Grenzwert"}
CLOSED_MEANWHILE = (
    "Die Kampagne wurde inzwischen abgeschlossen. Die Änderung an der Messung ist nicht gespeichert."
)


class MeasurementEditing:
    """Compares the fields with the stored row; only differences are written."""

    def changes(self) -> dict[str, str]:
        if self.row is None:
            return {}
        current = {
            "function": self.function.currentData(),
            "location": self.location.text().strip(),
            "operator": self.operator.text().strip(),
            "comment": self.comment.toPlainText().strip(),
            "verdict": self.verdict.currentData(),
        }
        return {field: new for field, new in current.items() if new != self.row[field]}

    @property
    def dirty(self) -> bool:
        return bool(self.changes() or self.rows.changes())

    def marked_fields(self) -> list[str]:
        """What the protocol will show as changed, in the words of the form."""
        fields = list(self.changes())
        for value_fields in self.rows.changes().values():
            fields += value_fields
        names = [FIELD_NAMES[f] for f in fields if f not in TEXT_FIELDS and f in FIELD_NAMES]
        return list(dict.fromkeys(names))

    def _edited(self) -> None:
        if self._filling:
            return
        self.pending.setVisible(self.dirty)
        marked = self.marked_fields()
        self.pending_hint.setText(
            f"Im Protokoll als „geändert“ vermerkt: {', '.join(marked)}." if marked
            else "Textkorrektur, ohne Vermerk im Protokoll."
        )

    def apply(self) -> bool:
        """Writes what was changed. Returns whether anything was written."""
        if self.row is None or not self.dirty:
            return False
        try:
            self.app.service.edit_measurement(self.row["id"], self.changes(), self.rows.changes())
        except CampaignClosed:
            show_error(self, CLOSED_MEANWHILE)
            self.discard()
            return False
        self.row = self.app.db.one("SELECT * FROM measurements WHERE id=?", self.row["id"])
        self.rows.rows = self.app.service.values(self.row["id"])
        self._edited()
        self.changed.emit()
        return True

    def discard(self) -> None:
        row, self.row = self.row, None
        self.show_row(row, self.editable, self.capture)
