# EasyMeasurement - easymeasurement/ui/element_form.py
# One element of the structure: its name, kind, interval and the features its kind offers.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..l10n import N_, plural, tr
from .choice_box import feature_field, field_text
from .common import AppContext, show_error
from .kind_catalog import KindCatalog
from .overlay import Overlay

TEXTS = {"name": N_("Designation"), "identifier": N_("Identifier"),
         "manufacturer": N_("Manufacturer"), "type": N_("Type designation"),
         "serial_no": N_("Serial number"), "comment": N_("Remark"), "basis": N_("Test basis")}
AS_KIND = -1  # the interval spin box's value for "as the kind says"


def interval_text(months: int) -> str:
    if not months:
        return tr("no repetition")
    return plural(months, "every month", "every {count} months")


class ElementForm(QWidget):
    """Every field writes itself back when the cursor leaves it, so nothing typed is lost."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.asset_id: int | None = None
        self.live = True  # every finished field is stored; otherwise only by `save`
        self.catalog = KindCatalog(app.db)
        self.fields = {key: QLineEdit() for key in TEXTS}
        self.kind = QComboBox()
        self.kind.activated.connect(lambda _: self._kind_chosen())
        self.interval = QSpinBox(minimum=AS_KIND, maximum=240, suffix=tr(" months"))
        self.interval.setSpecialValueText(tr("as the kind"))
        self.interval.editingFinished.connect(self._edited)
        self.interval_hint = QLabel()
        self.interval_hint.setEnabled(False)
        form = QFormLayout()
        form.addRow(tr(TEXTS["name"]), self.fields["name"])
        form.addRow(tr("Kind"), self.kind)
        for key in ("identifier", "manufacturer", "type", "serial_no", "comment", "basis"):
            form.addRow(tr(TEXTS[key]), self.fields[key])
        self.basis_hint = QLabel(tr("The top element needs a test basis; those below follow it."))
        self.basis_hint.setStyleSheet("color: #c0392b;")
        self.basis_hint.setWordWrap(True)
        self.basis_hint.hide()
        form.addRow("", self.basis_hint)
        repeat = QHBoxLayout()
        repeat.addWidget(self.interval)
        repeat.addWidget(self.interval_hint, 1)
        form.addRow(tr("Inspection interval"), repeat)
        for field in self.fields.values():
            field.editingFinished.connect(self._edited)
        self.features = QGroupBox(tr("Features"))
        self.feature_form = QFormLayout(self.features)
        self.feature_fields: dict[str, QLineEdit | QComboBox] = {}
        hint = QLabel(tr("Empty features appear nowhere, not even in the report."))
        hint.setEnabled(False)
        hint.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self._scrolled(self.features, hint), 1)

    def _scrolled(self, *widgets: QWidget) -> QScrollArea:
        """The features keep the height of their rows; where the room left below the fields
        is too small for them, they scroll."""
        inner = QWidget()
        column = QVBoxLayout(inner)
        column.setContentsMargins(0, 0, 0, 0)
        for widget in widgets:
            column.addWidget(widget)
        column.addStretch(1)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setFrameShape(QFrame.Shape.NoFrame)
        area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        area.setMinimumHeight(4 * self.fontMetrics().height() * 2)
        area.viewport().setAutoFillBackground(False)
        inner.setAutoFillBackground(False)
        area.setWidget(inner)
        return area

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
        self._show_basis(row)
        self._show_features(row["kind"])
        self._hint()

    def _show_features(self, kind_key: str) -> None:
        while self.feature_form.rowCount():
            self.feature_form.removeRow(0)
        self.feature_fields.clear()
        kind = self.catalog.by_key.get(kind_key)
        values = self.app.db.asset_features(self.asset_id)
        for feature in kind.features if kind else ():
            field = feature_field(feature, values.get(feature.key, ""))
            editor = field.lineEdit() if isinstance(field, QComboBox) else field
            editor.editingFinished.connect(self._edited)
            if isinstance(field, QComboBox):
                field.activated.connect(lambda _: self._edited())
            self.feature_fields[feature.key] = field
            row = QHBoxLayout()
            row.addWidget(field, 1)
            unit = QLabel(feature.unit)
            unit.setFixedWidth(self.fontMetrics().horizontalAdvance("1/min") + 4)
            row.addWidget(unit)
            self.feature_form.addRow(feature.label, row)
        self.features.setTitle(tr("Features: {kind}", kind=kind.label) if kind else tr("Features"))
        self.features.setVisible(bool(self.feature_fields))

    def _edited(self) -> None:
        if self.live:
            self.save()

    def _kind_chosen(self) -> None:
        self._edited()
        self._show_features(self.kind.currentData())
        self._hint()

    def _hint(self) -> None:
        kind = self.catalog.by_key.get(self.kind.currentData())
        months = kind.interval_months if kind else 0
        own = self.interval.value()
        self.interval_hint.setText(
            tr("Kind: {interval}", interval=interval_text(months)) if own == AS_KIND
            else interval_text(own)
        )

    def save(self) -> None:
        """Values of features the kind no longer offers stay stored, they only stop showing."""
        if self.asset_id is None or self.app.db.asset(self.asset_id) is None:
            return
        stored = self.app.db.asset(self.asset_id)
        values = {key: field.text().strip() for key, field in self.fields.items()}
        if not values["name"]:
            self.fields["name"].setText(stored["name"])
            show_error(self, tr("The element needs a designation."))
            return
        kind = self.kind.currentData()
        changed = kind != stored["kind"] or any(values[k] != stored[k] for k in values)
        if changed:
            self.app.db.update_asset(self.asset_id, kind, **values)
            if values["name"] != stored["name"]:
                self.app.service.rename_element(self.asset_id, values["name"])
        features = self.app.db.asset_features(self.asset_id)
        typed = {key: field_text(field) for key, field in self.feature_fields.items()}
        if any(features.get(k, "") != v.strip() for k, v in typed.items()):
            self.app.db.set_asset_features(self.asset_id, {**features, **typed})
            changed = True
        own = None if self.interval.value() == AS_KIND else self.interval.value()
        if own != stored["interval_months"]:
            self.app.db.set_asset_interval(self.asset_id, own)
            changed = True
        self._hint()
        self._show_basis(self.app.db.asset(self.asset_id))
        if changed:
            self.changed.emit()

    def _show_basis(self, row) -> None:
        """An empty test basis follows the element above, which the field shows greyed."""
        followed = self.app.db.test_basis(row["parent_id"])[1] if row["parent_id"] else ""
        field = self.fields["basis"]
        field.setPlaceholderText(tr("as above: {basis}", basis=followed) if followed else
                                 tr("e.g. DIN VDE 0100-600"))
        self.basis_hint.setVisible(row["parent_id"] is None and not row["basis"])


class ElementOverlay(Overlay):
    def __init__(self, app: AppContext, asset_id: int, parent=None):
        super().__init__(tr("Properties"), parent, width=560)
        self.ok_button.setText(tr("Apply"))
        self.form = ElementForm(app)
        self.form.live = False  # Cancel leaves the element as it was
        self.form.load(asset_id)
        self.body.addWidget(self.form)

    def first_field(self):
        return self.form.fields["name"]

    def accept(self) -> None:
        self.form.save()
        super().accept()
