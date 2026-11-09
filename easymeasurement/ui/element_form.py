# EasyMeasurement - easymeasurement/ui/element_form.py
# One element of the structure: its name, kind, interval and the features its kind offers.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .common import AppContext, show_error
from .kind_catalog import KindCatalog
from .overlay import Overlay

TEXTS = {"name": "Bezeichnung", "identifier": "Kennung", "manufacturer": "Hersteller",
         "type": "Typbezeichnung", "serial_no": "Seriennummer", "comment": "Bemerkung"}
AS_KIND = -1  # the interval spin box's value for "as the kind says"


def interval_text(months: int) -> str:
    return "keine Wiederholung" if not months else f"alle {months} Monate"


class ElementForm(QWidget):
    """Every field writes itself back when the cursor leaves it, so nothing typed is lost."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.asset_id: int | None = None
        self.catalog = KindCatalog(app.db)
        self.fields = {key: QLineEdit() for key in TEXTS}
        self.kind = QComboBox()
        self.kind.activated.connect(lambda _: self._kind_chosen())
        self.interval = QSpinBox(minimum=AS_KIND, maximum=240, suffix=" Monate")
        self.interval.setSpecialValueText("wie der Typ")
        self.interval.editingFinished.connect(self.save)
        self.interval_hint = QLabel()
        self.interval_hint.setEnabled(False)
        form = QFormLayout()
        form.addRow(TEXTS["name"], self.fields["name"])
        form.addRow("Typ", self.kind)
        for key in ("identifier", "manufacturer", "type", "serial_no", "comment"):
            form.addRow(TEXTS[key], self.fields[key])
        repeat = QHBoxLayout()
        repeat.addWidget(self.interval)
        repeat.addWidget(self.interval_hint, 1)
        form.addRow("Prüfintervall", repeat)
        for field in self.fields.values():
            field.editingFinished.connect(self.save)
        self.features = QGroupBox("Merkmale")
        self.feature_form = QFormLayout(self.features)
        self.feature_fields: dict[str, QLineEdit] = {}
        hint = QLabel("Leere Merkmale erscheinen nirgends, auch nicht im Protokoll.")
        hint.setEnabled(False)
        hint.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self.features)
        layout.addWidget(hint)
        layout.addStretch(1)

    def load(self, asset_id: int) -> None:
        self.asset_id = asset_id
        self.catalog = KindCatalog(self.app.db)
        row = self.app.db.asset(asset_id)
        for key, field in self.fields.items():
            field.setText(row[key])
        self.kind.clear()
        for kind in sorted(self.catalog.all, key=lambda k: k.label.casefold()):
            self.kind.addItem(self.catalog.icon(kind.key), kind.label, kind.key)
        self.kind.setCurrentIndex(self.kind.findData(row["kind"]))
        own = row["interval_months"]
        self.interval.setValue(AS_KIND if own is None else own)
        self._show_features(row["kind"])
        self._hint()

    def _show_features(self, kind_key: str) -> None:
        while self.feature_form.rowCount():
            self.feature_form.removeRow(0)
        self.feature_fields.clear()
        kind = self.catalog.by_key.get(kind_key)
        values = self.app.db.asset_features(self.asset_id)
        for feature in kind.features if kind else ():
            field = QLineEdit(values.get(feature.key, ""))
            field.editingFinished.connect(self.save)
            self.feature_fields[feature.key] = field
            row = QHBoxLayout()
            row.addWidget(field, 1)
            unit = QLabel(feature.unit)
            unit.setFixedWidth(self.fontMetrics().horizontalAdvance("1/min") + 4)
            row.addWidget(unit)
            self.feature_form.addRow(feature.label, row)
        self.features.setTitle(f"Merkmale: {kind.label}" if kind else "Merkmale")
        self.features.setVisible(bool(self.feature_fields))

    def _kind_chosen(self) -> None:
        self.save()
        self._show_features(self.kind.currentData())
        self._hint()

    def _hint(self) -> None:
        kind = self.catalog.by_key.get(self.kind.currentData())
        months = kind.interval_months if kind else 0
        own = self.interval.value()
        self.interval_hint.setText(
            f"Typ: {interval_text(months)}" if own == AS_KIND else interval_text(own)
        )

    def save(self) -> None:
        """Values of features the kind no longer offers stay stored, they only stop showing."""
        if self.asset_id is None or self.app.db.asset(self.asset_id) is None:
            return
        stored = self.app.db.asset(self.asset_id)
        values = {key: field.text().strip() for key, field in self.fields.items()}
        if not values["name"]:
            self.fields["name"].setText(stored["name"])
            show_error(self, "Das Element braucht eine Bezeichnung.")
            return
        kind = self.kind.currentData()
        changed = kind != stored["kind"] or any(values[k] != stored[k] for k in values)
        if changed:
            self.app.db.update_asset(self.asset_id, kind, **values)
            if values["name"] != stored["name"]:
                self.app.service.rename_element(self.asset_id, values["name"])
        features = self.app.db.asset_features(self.asset_id)
        typed = {key: field.text() for key, field in self.feature_fields.items()}
        if any(features.get(k, "") != v.strip() for k, v in typed.items()):
            self.app.db.set_asset_features(self.asset_id, {**features, **typed})
            changed = True
        own = None if self.interval.value() == AS_KIND else self.interval.value()
        if own != stored["interval_months"]:
            self.app.db.set_asset_interval(self.asset_id, own)
            changed = True
        self._hint()
        if changed:
            self.changed.emit()


class ElementOverlay(Overlay):
    def __init__(self, app: AppContext, asset_id: int, parent=None):
        super().__init__("Eigenschaften", parent, width=560)
        self.ok_button.setText("Fertig")
        self.cancel_button.hide()
        self.form = ElementForm(app)
        self.form.load(asset_id)
        self.body.addWidget(self.form)

    def first_field(self):
        return self.form.fields["name"]

    def accept(self) -> None:
        self.form.save()
        super().accept()
