# OkeyDocu - okeydocu/ui/measurement_editor.py
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

from ..l10n import N_, moment, tr
from ..model import CONDUCTOR
from ..vocabulary import function_keys, function_label
from ..devices import setting_words
from .common import AppContext, function_short, stored_parameters
from .attachment_list import AttachmentList
from .growing_edit import GrowingEdit
from .measurement_editing import MeasurementEditing
from .place_line import PlaceLine
from .value_rows import QuietCombo, ValueRows, verdict_combo

READ_ONLY_STYLE = "background: transparent; border: none;"
LOCKED_TEXT = N_("The campaign is completed. The measurement can only be read.")


def _facts(row, capture: str, db) -> str:
    """When, how, and the instrument's settings in words; one still a code is left out."""
    when = datetime.fromisoformat(row["local_time"])
    words = setting_words(db)
    extra = []
    for parameter in stored_parameters(row):
        name, value, said = words.say(parameter.key, parameter.value)
        if parameter.key != CONDUCTOR and said:
            extra.append(f"{name}: {value}")
    return " · ".join([moment(when, seconds=True), capture, *extra])


HINT_PLACEHOLDER = N_("How to measure here")
HINT_TIP = N_("How to measure here. Appears again at the repeat inspection; the report shows it"
              " beneath the measurement's photos marked as a notice.")
LOCATION_PLACEHOLDER = N_("Where it was measured")
COMMENT_PLACEHOLDER = N_("Remark on the measurement")


class MeasurementEditor(MeasurementEditing, QWidget):
    """Nothing is written while typing.

    Apply, Ctrl+Enter or moving on to another measurement writes what was
    changed; Discard and Esc bring back what is stored. The bar above the buttons
    says beforehand which changes the protocol will mark.
    """

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.row = None
        self.editable, self.capture = False, ""
        self._filling = False
        self.title = QLabel(tr("No measurement selected."))
        self.title.setWordWrap(True)
        font = self.title.font()
        font.setBold(True)
        self.title.setFont(font)
        self.facts = QLabel()
        self.facts.setWordWrap(True)
        self.facts.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.function = QuietCombo()
        for key in function_keys():
            self.function.addItem(function_label(key), key)
        self.location = QLineEdit(placeholderText=tr(LOCATION_PLACEHOLDER))
        # Booked onto an element, the element says where; the text is for what has none.
        self.place = PlaceLine(app)
        self.movable = False  # the view offers booking elsewhere
        self.where = where = QWidget()
        where_layout = QVBoxLayout(where)
        where_layout.setContentsMargins(0, 0, 0, 0)
        where_layout.addWidget(self.place)
        where_layout.addWidget(self.location)
        self.operator = QLineEdit()
        self.verdict = verdict_combo("")
        self.comment = GrowingEdit(tr(COMMENT_PLACEHOLDER))
        self.hint = GrowingEdit(tr(HINT_PLACEHOLDER))
        self.hint.setToolTip(tr(HINT_TIP))
        self.rows = ValueRows()
        self.values = self.rows.table
        # The measurement has its remark field, so only files are attached; images join its photos.
        self.attachments = AttachmentList(app, tr("Note on this measurement"), self._add_photo,
                                          notes=False)
        self.attachments.changed.connect(self.changed)
        self.locked = QLabel(tr(LOCKED_TEXT))
        self.locked.setWordWrap(True)
        self.form = QWidget()
        form = QFormLayout(self.form)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow(tr("Designation"), self.function)
        form.addRow(tr("Measuring location"), where)
        form.addRow(tr("Inspector"), self.operator)
        form.addRow(tr("Verdict"), self.verdict)
        form.addRow(tr("Remark"), self.comment)
        form.addRow(tr("Hint"), self.hint)

        self.pending = QWidget()
        self.pending_hint = QLabel()
        self.pending_hint.setWordWrap(True)
        self.discard_button = QPushButton(tr("Discard"))
        self.discard_button.clicked.connect(self.discard)
        self.apply_button = QPushButton(tr("Apply"))
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
        self.hint.textChanged.connect(self._edited)
        self.rows.edited.connect(self._edited)
        self._keys(self)
        self.show_row(None, False)

    def take_out(self) -> tuple[QWidget, QWidget]:
        """The readings and the files leave the editor for places of their own; the keys
        that apply or discard go with them."""
        for part in (self.values, self.attachments):
            self.layout().removeWidget(part)
            self._keys(part)
        return self.values, self.attachments

    def _keys(self, widget: QWidget) -> None:
        for keys in ("Ctrl+Return", "Ctrl+Enter"):
            self._shortcut(widget, keys, self.apply)
        self._shortcut(widget, QKeySequence.StandardKey.Cancel, self.discard)

    @staticmethod
    def _shortcut(widget: QWidget, keys, slot) -> None:
        shortcut = QShortcut(QKeySequence(keys), widget)
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
            self.title.setText(tr("No measurement selected."))
            self.rows.fill([], False)
            self.attachments.show_target(None)
        else:
            self.title.setText(function_short(row["function"]))
            self.facts.setText(_facts(row, capture, self.app.db))
            if self.function.findData(row["function"]) < 0:
                self.function.addItem(row["function"], row["function"])
            self.function.setCurrentIndex(self.function.findData(row["function"]))
            self.verdict.setCurrentIndex(self.verdict.findData(row["verdict"]))
            self.location.setText(row["location"])
            booked = row["asset_id"] is not None
            if booked:
                self.place.show_asset(row["asset_id"], editable and self.movable)
            self.place.setVisible(booked)
            self.location.setVisible(not booked)
            # A tight side panel would press the two lines of the place into one.
            shown = self.place if booked else self.location
            self.where.setMinimumHeight(shown.sizeHint().height())
            self.operator.setText(row["operator"])
            self.comment.setPlainText(row["comment"])
            self.hint.setPlainText(row["hint"])
            self.rows.fill(self.app.service.values(row["id"]), editable)
            self.attachments.show_target(row["campaign_id"], editable, measurement_id=row["id"])
        self.location.setPlaceholderText(tr(LOCATION_PLACEHOLDER) if editable else "")
        self.comment.setPlaceholderText(tr(COMMENT_PLACEHOLDER) if editable else "")
        self.hint.setPlaceholderText(tr(HINT_PLACEHOLDER) if editable else "")
        for field in (self.location, self.operator, self.comment, self.hint):
            field.setReadOnly(not editable)
            # Read-only, a field reads as text rather than as a box waiting for input.
            field.setStyleSheet("" if editable else READ_ONLY_STYLE)
        self.comment.refit()
        self.hint.refit()
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
