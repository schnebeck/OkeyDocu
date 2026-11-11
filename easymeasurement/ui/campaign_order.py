# EasyMeasurement - easymeasurement/ui/campaign_order.py
# The client's and the contractor's side of a job, as both campaign dialogs ask for them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The contact person stays in view. What is given less often, the client's department and
lines and the contractor's own account and reference, folds away below; it opens by itself
where it already holds something. The fields are rows of the dialog's own form, so their
labels line up with the rest."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout, QLabel, QLineEdit, QToolButton

from ..campaign.editing import CONTACT_COLUMNS, ORDER_COLUMNS
from ..l10n import N_, tr

CONTACT = ("contact", N_("Contact person"), N_("e.g. Ms Sample"))
CLIENT = (("department", N_("Department"), N_("e.g. maintenance")),
          ("contact_phone", N_("Extension"), N_("e.g. 0511 1234-56")),
          ("contact_email", N_("Email"), N_("name@customer.example")))
CONTRACTOR = (("cost_center", N_("Cost centre"), N_("own cost centre for this job")),
              ("job_number", N_("Job number"), N_("own reference for this job")))


class OrderFields:
    """`values` maps the campaign columns to what they hold; missing ones start empty."""

    def __init__(self, form: QFormLayout, values: dict):
        self.form = form
        self.fields: dict[str, QLineEdit] = {}
        self.folded: list = []
        self.expanded = False
        self._add(*CONTACT, values)
        # Not a checkable button: open, it would look pressed.
        self.fold = QToolButton(autoRaise=True)
        self.fold.setText(tr("More about the order"))
        self.fold.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        form.addRow(self.fold)
        self._heading(tr("<b>Client</b>"))
        for key, label, hint in CLIENT:
            self._add(key, label, hint, values, folded=True)
        self._heading(tr("<b>Contractor</b>"))
        for key, label, hint in CONTRACTOR:
            self._add(key, label, hint, values, folded=True)
        self.fold.clicked.connect(lambda: self._show(not self.expanded))
        self._show(any(values.get(key) for key, _, _ in CLIENT + CONTRACTOR))

    def _heading(self, text: str) -> None:
        label = QLabel(text)
        self.form.addRow(label)
        self.folded.append(label)

    def _add(self, key: str, label: str, hint: str, values: dict, folded: bool = False) -> None:
        field = QLineEdit(values.get(key) or "")
        field.setPlaceholderText(tr(hint))
        self.form.addRow(tr(label), field)
        self.fields[key] = field
        if folded:
            self.folded.append(field)

    def _show(self, shown: bool) -> None:
        self.expanded = shown
        for widget in self.folded:
            self.form.setRowVisible(widget, shown)
        self.fold.setArrowType(Qt.ArrowType.DownArrow if shown else Qt.ArrowType.RightArrow)

    def fill(self, values: dict) -> None:
        """Puts in what `values` holds, as a suggestion; other fields keep their text."""
        for key, value in values.items():
            if key in self.fields:
                self.fields[key].setText(value or "")
        if any(values.get(key) for key, _, _ in CLIENT + CONTRACTOR):
            self._show(True)

    def contact_values(self) -> tuple[str, ...]:
        return tuple(self.fields[key].text().strip() for key in CONTACT_COLUMNS)

    def order_values(self) -> tuple[str, ...]:
        return tuple(self.fields[key].text().strip() for key in ORDER_COLUMNS)
