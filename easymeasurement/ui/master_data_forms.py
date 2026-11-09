# EasyMeasurement - easymeasurement/ui/master_data_forms.py
# A customer's address, written back field by field.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from .common import AppContext, show_error

CUSTOMER_LABELS = {"name": "Name", "street": "Straße", "zip": "PLZ", "city": "Ort",
                   "comment": "Kommentar"}
SAVED_HINT = "Änderungen gelten beim Verlassen des Felds."


class CustomerForm(QWidget):
    """Fields write themselves back when the cursor leaves them, so nothing typed is lost."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.customer_id: int | None = None
        self.fields = {key: QLineEdit() for key in CUSTOMER_LABELS}
        form = QFormLayout()
        for key, label in CUSTOMER_LABELS.items():
            form.addRow(label, self.fields[key])
            self.fields[key].editingFinished.connect(self.save)
        hint = QLabel(SAVED_HINT)
        hint.setEnabled(False)
        form.addRow("", hint)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addStretch(1)

    def load(self, customer_id: int) -> None:
        self.customer_id = customer_id
        row = self.app.db.customer(customer_id)
        for key, field in self.fields.items():
            field.setText(row[key])

    def save(self) -> None:
        """A name may not be empty; an empty one brings the stored name back."""
        if self.customer_id is None or self.app.db.customer(self.customer_id) is None:
            return
        values = {key: field.text().strip() for key, field in self.fields.items()}
        stored = self.app.db.customer(self.customer_id)
        if not values["name"]:
            self.fields["name"].setText(stored["name"])
            show_error(self, "Der Kunde braucht einen Namen.")
            return
        if any(values[key] != stored[key] for key in values):
            self.app.db.update_customer(self.customer_id, **values)
            self.changed.emit()
