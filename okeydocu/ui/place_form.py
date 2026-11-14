# OkeyDocu - okeydocu/ui/place_form.py
# Station "Installation", right side: which element, and what the guide needs it to state.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A missing statement is marked, not demanded: going on without it keeps the measurement
possible and the drawing in its usual layout. Where the element is still to be made, its name
and identifier are asked for as well; the structure grows while measuring. What is entered is
stored when the tester goes on, as if entered in the element's own form."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..campaign.measuring_place import MeasuringPlace
from ..devices.guide import Guide
from ..l10n import N_, tr
from .choice_box import feature_field, field_text
from .choice_tips import choice_text
from .pending_marks import PendingMarks

MISSING_STYLE = "background:#fde2c4"
HINT = "#b35c00"
NEW = -1  # the choice that makes an element
PARENT_TIP = N_("The element the new one is placed below in the structure, such as the"
                " distribution board the RCD sits in. The choice stays for every further new"
                " element of this campaign until it is changed.")


class PlaceForm(QWidget):
    element_chosen = Signal(int)  # an existing element, or NEW
    parent_chosen = Signal(int)  # where a new element is to hang
    edited = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.place = MeasuringPlace(None)
        self.fields: dict[str, QWidget] = {}
        self.name = QLineEdit()
        self.identifier = QLineEdit()
        for line in (self.name, self.identifier):
            line.textEdited.connect(lambda _: self.edited.emit())
        self.parent_box = QComboBox()
        self.parent_box.activated.connect(lambda index: self.parent_chosen.emit(
            self.parent_box.itemData(index)))
        self.choice = QComboBox()
        self.choice.activated.connect(lambda index: self.element_chosen.emit(
            self.choice.itemData(index)))
        self.new_title = QLabel(f"<b>{tr('New element')}</b>")
        self.new_form = QFormLayout()
        self.parent_box.setToolTip(tr(PARENT_TIP))
        self.new_form.addRow(tr("Parent element"), self.parent_box)
        self.new_form.addRow(tr("Designation"), self.name)
        self.new_form.addRow(tr("Identifier"), self.identifier)
        self.form = QFormLayout()
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.data_title = QLabel()
        self.pending_marks = PendingMarks(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"<b>{tr('Where do we measure?')}</b>"))
        layout.addWidget(self.choice)
        layout.addSpacing(8)
        layout.addWidget(self.new_title)
        layout.addLayout(self.new_form)
        layout.addSpacing(8)
        layout.addWidget(self.data_title)
        layout.addLayout(self.form)
        layout.addWidget(self.hint)

    def show_place(self, guide: Guide, place: MeasuringPlace,
                   candidates: list[tuple[int, str]], parents: list[tuple[int, str]] = (),
                   parent_id: int | None = None) -> None:
        self.place = place
        self.parent_box.clear()
        for asset_id, path in parents:
            self.parent_box.addItem(path, asset_id)
        self.parent_box.setCurrentIndex(max(self.parent_box.findData(parent_id), 0))
        self.new_title.setVisible(place.is_new)
        for row in range(self.new_form.rowCount()):
            self.new_form.setRowVisible(row, place.is_new)
        self.choice.clear()
        for asset_id, title in candidates:
            self.choice.addItem(title, asset_id)
        if place.kind and guide.owner_feature:
            kind_label = tr(self.app.db.kind(place.kind).label)
            self.choice.addItem(tr("＋ New {kind} …", kind=kind_label), NEW)
        self.choice.setCurrentIndex(max(self.choice.findData(
            NEW if place.is_new else place.asset_id), 0))
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields.clear()
        if not place.kind:
            self.data_title.setText("")
            self.hint.setText(f"<span style='color:{HINT}'>"
                              f"{tr('Choose the element this test is for.')}</span>")
            return
        if place.is_new:
            self.name.setPlaceholderText(tr(self.app.db.kind(place.kind).label))
        self._feature_rows(guide, place)

    def _feature_rows(self, guide: Guide, place: MeasuringPlace) -> None:
        kind = self.app.db.kind(place.kind)
        lists = self.app.db.choice_lists()
        features = {feature.key: feature for feature in kind.features}
        self.data_title.setText(f"<b>{tr('Details from the rating plate')}</b>")
        for key in guide.element_features:
            if key not in features:
                continue
            field = feature_field(features[key], str(place.features.get(key) or ""), lists)
            field.setStyleSheet(MISSING_STYLE if key in place.missing([key]) else "")
            above = place.inherited.get(key, "")
            if above and not place.features.get(key):
                edit = field.lineEdit() if isinstance(field, QComboBox) else field
                edit.setPlaceholderText(tr("{value}, as stated above", value=choice_text(above)))
            edits = field.editTextChanged if isinstance(field, QComboBox) else field.textEdited
            edits.connect(lambda text, field=field, above=above: self._typed(field, text, above))
            self.fields[key] = field
            unit = features[key].unit
            self.form.addRow(tr(features[key].label) + (f" ({unit})" if unit else ""), field)
        hint = tr("Missing details are stored at the element. Without them the drawing shows"
                  " the usual layout.")
        missing = place.missing(self.fields)
        self.hint.setText(f"<span style='color:{HINT}'>{hint}</span>" if missing else "")
        self.pending_marks.watch()

    def _typed(self, field, text: str, above: str = "") -> None:
        field.setStyleSheet("" if text.strip() or above else MISSING_STYLE)
        self.edited.emit()

    def entered(self) -> dict[str, str]:
        """What differs from what the element stated."""
        values = {key: self._value(field) for key, field in self.fields.items()}
        return {key: value for key, value in values.items()
                if value != str(self.place.features.get(key) or "").strip()}

    def title(self) -> str:
        """Name and identifier of an element still to be made, as they read so far."""
        name = self.name.text().strip() or self.name.placeholderText()
        return " ".join(part for part in (self.identifier.text().strip(), name) if part)

    @staticmethod
    def _value(field) -> str:
        return field_text(field).strip()

    def store(self) -> bool:
        """Stores what was entered at an existing element; whether anything changed."""
        changed = self.entered()
        if changed and self.place.asset_id is not None:
            features = dict(self.place.features)
            features.update(changed)
            self.app.db.set_asset_features(self.place.asset_id, features)
        return bool(changed)
