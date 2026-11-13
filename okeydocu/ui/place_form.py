# OkeyDocu - okeydocu/ui/place_form.py
# Station "Installation", right side: which element, and what the guide needs it to state.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A missing statement is marked, not demanded: going on without it keeps the measurement
possible and the drawing in its usual layout. What is entered here is stored at the element
when the tester goes on, as if entered in the element's own form."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QFormLayout, QLabel, QVBoxLayout, QWidget

from ..campaign.measuring_place import MeasuringPlace
from ..devices.guide import Guide
from ..l10n import tr
from .choice_box import ChoiceBox, feature_field, field_text
from .choice_tips import held_value

MISSING_STYLE = "background:#fde2c4"
HINT = "#b35c00"


class PlaceForm(QWidget):
    element_chosen = Signal(int)
    edited = Signal()

    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.place = MeasuringPlace(None)
        self.fields: dict[str, QWidget] = {}
        self.choice = QComboBox()
        self.choice.activated.connect(self._chosen)
        self.form = QFormLayout()
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"<b>{tr('Where do we measure?')}</b>"))
        layout.addWidget(self.choice)
        layout.addSpacing(8)
        self.data_title = QLabel()
        layout.addWidget(self.data_title)
        layout.addLayout(self.form)
        layout.addWidget(self.hint)

    def show_place(self, guide: Guide, place: MeasuringPlace,
                   candidates: list[tuple[int, str]]) -> None:
        self.place = place
        self.choice.clear()
        for asset_id, title in candidates:
            self.choice.addItem(title, asset_id)
        if place.asset_id is None:
            self.choice.insertItem(0, tr("— choose —"), None)
        self.choice.setCurrentIndex(max(self.choice.findData(place.asset_id), 0))
        while self.form.rowCount():
            self.form.removeRow(0)
        self.fields.clear()
        if place.asset_id is None:
            self.data_title.setText("")
            self.hint.setText(f"<span style='color:{HINT}'>"
                              f"{tr('Choose the element this test is for.')}</span>")
            return
        kind = self.app.db.kind(self.app.db.asset(place.asset_id)["kind"])
        lists = self.app.db.choice_lists()
        features = {feature.key: feature for feature in kind.features}
        self.data_title.setText(f"<b>{tr('Details from the rating plate')}</b>")
        for key in guide.element_features:
            if key not in features:
                continue
            field = feature_field(features[key], str(place.features.get(key) or ""), lists)
            if key in place.missing([key]):
                field.setStyleSheet(MISSING_STYLE)
            self.fields[key] = field
            unit = features[key].unit
            label = tr(features[key].label) + (f" ({unit})" if unit else "")
            self.form.addRow(label, field)
        hint = tr("Missing details are stored at the element. Without them the drawing shows"
                  " the usual layout.")
        missing = place.missing(self.fields)
        self.hint.setText(f"<span style='color:{HINT}'>{hint}</span>" if missing else "")

    def entered(self) -> dict[str, str]:
        """What differs from what the element stated."""
        values = {key: self._value(field) for key, field in self.fields.items()}
        return {key: value for key, value in values.items()
                if value != str(self.place.features.get(key) or "").strip()}

    @staticmethod
    def _value(field) -> str:
        """A word of a list is stored as the list holds it, not as shown in the language."""
        text = field_text(field).strip()
        if isinstance(field, ChoiceBox) and text:
            return held_value(field.list, text) or text
        return text

    def store(self) -> bool:
        """Stores what was entered at the element; whether anything changed."""
        changed = self.entered()
        if changed and self.place.asset_id is not None:
            features = dict(self.place.features)
            features.update(changed)
            self.app.db.set_asset_features(self.place.asset_id, features)
        return bool(changed)

    def _chosen(self, index: int) -> None:
        asset_id = self.choice.itemData(index)
        if asset_id is not None:
            self.element_chosen.emit(asset_id)
