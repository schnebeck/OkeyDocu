# EasyMeasurement - easymeasurement/ui/measurement_editor.py
# The selected measurement beside the table, corrected in place while its campaign is open.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..model import CONDUCTOR, FUNCTION_LABELS
from .common import AppContext, function_short, stored_parameters
from .attachment_list import AttachmentList
from .growing_edit import GrowingEdit
from .measurement_editing import MeasurementEditing
from .value_rows import QuietCombo, ValueRows, verdict_combo

READ_ONLY_STYLE = "background: transparent; border: none;"
LOCKED_TEXT = "Die Kampagne ist abgeschlossen. Die Messung lässt sich nur lesen."


def _facts(row, capture: str) -> str:
    when = datetime.fromisoformat(row["local_time"])
    extra = [
        f"{p.key}: {p.value}" for p in stored_parameters(row)
        if not p.key.startswith("TS") and not p.value.startswith("TS") and p.key != CONDUCTOR
    ]
    return " · ".join([f"{when:%d.%m.%Y %H:%M:%S}", capture, *extra])


class MeasurementEditor(MeasurementEditing, QWidget):
    """Nothing is written while typing.

    Übernehmen, Ctrl+Enter or moving on to another measurement writes what was
    changed; Verwerfen and Esc bring back what is stored. The bar above the buttons
    says beforehand which changes the protocol will mark.
    """

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.row = None
        self.editable, self.capture = False, ""
        self._filling = False
        self.title = QLabel("Keine Messung gewählt.")
        self.title.setWordWrap(True)
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        self.facts = QLabel()
        self.facts.setWordWrap(True)
        self.facts.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.function = QuietCombo()
        for key, label in FUNCTION_LABELS.items():
            self.function.addItem(label, key)
        self.location = QLineEdit(placeholderText="Wo gemessen wurde")
        self.operator = QLineEdit()
        self.verdict = verdict_combo("")
        self.comment = GrowingEdit("Bemerkung zur Messung")
        self.rows = ValueRows()
        self.values = self.rows.table
        # The measurement has its remark field, so only files are attached; images join its photos.
        self.attachments = AttachmentList(app, "dieser Messung", self._add_photo, notes=False)
        self.attachments.changed.connect(self.changed)
        self.locked = QLabel(LOCKED_TEXT)
        self.locked.setWordWrap(True)
        self.form = QWidget()
        form = QFormLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Funktion", self.function)
        form.addRow("Messort", self.location)
        form.addRow("Prüfer", self.operator)
        form.addRow("Bewertung", self.verdict)
        form.addRow("Bemerkung", self.comment)

        self.pending = QWidget()
        self.pending_hint = QLabel()
        self.pending_hint.setWordWrap(True)
        self.discard_button = QPushButton("Verwerfen")
        self.discard_button.clicked.connect(self.discard)
        self.apply_button = QPushButton("Übernehmen")
        self.apply_button.setDefault(True)
        self.apply_button.clicked.connect(self.apply)
        bar = QHBoxLayout(self.pending)
        bar.setContentsMargins(0, 0, 0, 0)
        bar.addWidget(self.pending_hint, 1)
        bar.addWidget(self.discard_button)
        bar.addWidget(self.apply_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title)
        layout.addWidget(self.facts)
        layout.addWidget(self.form)
        layout.addWidget(self.values)
        layout.addWidget(self.attachments)
        layout.addWidget(self.locked)
        layout.addWidget(self.pending)
        layout.addStretch(1)

        for field in (self.location, self.operator):
            field.textEdited.connect(self._edited)
        for box in (self.function, self.verdict):
            box.currentIndexChanged.connect(self._edited)
        self.comment.textChanged.connect(self._edited)
        self.rows.edited.connect(self._edited)
        for keys in ("Ctrl+Return", "Ctrl+Enter"):
            self._shortcut(keys, self.apply)
        self._shortcut(QKeySequence.StandardKey.Cancel, self.discard)
        self.show_row(None, False)

    def _shortcut(self, keys, slot) -> None:
        shortcut = QShortcut(QKeySequence(keys), self)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(slot)

    # Showing -------------------------------------------------------------

    def show_row(self, row, editable: bool, capture: str = "") -> None:
        """A row that is being edited stays as typed when it is shown again."""
        if row is not None and self.row is not None and row["id"] == self.row["id"] and self.dirty:
            return
        self.row, self.editable, self.capture = row, editable, capture
        self._filling = True
        self.form.setVisible(row is not None)
        self.facts.setVisible(row is not None)
        self.locked.setVisible(row is not None and not editable)
        if row is None:
            self.title.setText("Keine Messung gewählt.")
            self.rows.fill([], False)
            self.attachments.show_target(None)
        else:
            self.title.setText(function_short(row["function"]))
            self.facts.setText(_facts(row, capture))
            if self.function.findData(row["function"]) < 0:
                self.function.addItem(row["function"], row["function"])
            self.function.setCurrentIndex(self.function.findData(row["function"]))
            self.verdict.setCurrentIndex(self.verdict.findData(row["verdict"]))
            self.location.setText(row["location"])
            self.operator.setText(row["operator"])
            self.comment.setPlainText(row["comment"])
            self.rows.fill(self.app.service.values(row["id"]), editable)
            self.attachments.show_target(row["campaign_id"], editable, measurement_id=row["id"])
        self.location.setPlaceholderText("Wo gemessen wurde" if editable else "")
        self.comment.setPlaceholderText("Bemerkung zur Messung" if editable else "")
        for field in (self.location, self.operator, self.comment):
            field.setReadOnly(not editable)
            # Read-only, a field reads as text rather than as a box waiting for input.
            field.setStyleSheet("" if editable else READ_ONLY_STYLE)
        self.comment.refit()
        for box in (self.function, self.verdict):
            box.setEnabled(editable)
        self._filling = False
        self._edited()

    def _add_photo(self, path) -> None:
        self.app.service.add_photo(self.row["id"], path)

    def focus_field(self, name: str = "comment") -> None:
        if self.row is None:
            return
        if name == "values":
            self.rows.focus_first()
            return
        field = getattr(self, name)
        field.setFocus()
        if isinstance(field, QLineEdit):
            field.selectAll()
