# EasyMeasurement - easymeasurement/ui/measurement_search.py
# The search for measurements across all campaigns.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QDate, QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QGridLayout,
    QHBoxLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..model import FUNCTION_LABELS, Quantity
from ..store.search import MeasurementFilter
from .board import GutterSplitter
from .common import AppContext
from .measurement_view import MeasurementView

_ANY = None


class MeasurementsPage(MeasurementView):
    """Finds measurements across all campaigns."""

    hide_empty_gallery = True

    def __init__(self, app: AppContext):
        super().__init__(app)
        self._debounce = QTimer(self, singleShot=True, interval=200)
        self._debounce.timeout.connect(self.refresh)

        self.text = QLineEdit(placeholderText="Suchen: Kunde, Anlage, Kommentar, Messwert …")
        self.text.setClearButtonEnabled(True)
        self.customer = QComboBox()
        self.asset = QComboBox()
        self.campaign = QComboBox()
        self.function = QComboBox()
        self.verdict = QComboBox()
        self.photos_only = QCheckBox("nur mit Foto")
        self.use_from, self.use_to = QCheckBox("von"), QCheckBox("bis")
        self.date_from = QDateEdit(QDate.currentDate().addMonths(-1), calendarPopup=True)
        self.date_to = QDateEdit(QDate.currentDate(), calendarPopup=True)
        self.value_key = QComboBox()
        self.value_min = QLineEdit(placeholderText="min, z. B. 1MΩ")
        self.value_max = QLineEdit(placeholderText="max, z. B. 500mΩ")
        # Long names of customers and campaigns must not widen the window.
        for combo in (self.customer, self.asset, self.campaign, self.function, self.value_key):
            combo.setSizeAdjustPolicy(
                QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
            )
            combo.setMinimumContentsLength(14)

        self.function.addItem("Alle Messungen und Prüfungen", _ANY)
        for key, label in FUNCTION_LABELS.items():
            self.function.addItem(label, key)
        self.verdict.addItem("Jede Bewertung", _ANY)
        self.verdict.addItem("bestanden", "passed")
        self.verdict.addItem("nicht bestanden", "failed")
        self.verdict.addItem("nicht bewertet", "not_evaluated")

        filters = QGridLayout()
        filters.addWidget(self.text, 0, 0, 1, 4)
        filters.addWidget(self.customer, 0, 4)
        filters.addWidget(self.asset, 0, 5)
        filters.addWidget(self.campaign, 0, 6)
        filters.addWidget(self.function, 1, 0)
        filters.addWidget(self.verdict, 1, 1)
        dates = QHBoxLayout()
        for widget in (self.use_from, self.date_from, self.use_to, self.date_to):
            dates.addWidget(widget)
        filters.addLayout(dates, 1, 2, 1, 2)
        filters.addWidget(self.value_key, 1, 4)
        values = QHBoxLayout()
        values.addWidget(self.value_min)
        values.addWidget(self.value_max)
        filters.addLayout(values, 1, 5)
        filters.addWidget(self.photos_only, 1, 6)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.addWidget(self.detail)
        detail_layout.addWidget(self.gallery, 1)
        splitter = GutterSplitter(objectName="search")
        splitter.addWidget(self.table)
        splitter.addWidget(detail)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 0)
        splitter.setSizes([980, 320])

        layout = QVBoxLayout(self)
        layout.addLayout(filters)
        layout.addLayout(self.actions_row)
        layout.addWidget(self.common)
        layout.addWidget(splitter, 1)

        self.reload_choices()
        self.text.textChanged.connect(lambda: self._debounce.start())
        self.value_min.textChanged.connect(lambda: self._debounce.start())
        self.value_max.textChanged.connect(lambda: self._debounce.start())
        for combo in (self.customer, self.asset, self.campaign, self.function, self.verdict,
                      self.value_key):
            combo.currentIndexChanged.connect(self.refresh)
        for box in (self.use_from, self.use_to, self.photos_only):
            box.toggled.connect(self.refresh)
        self.date_from.dateChanged.connect(self.refresh)
        self.date_to.dateChanged.connect(self.refresh)
        self.customer.currentIndexChanged.connect(self._customer_changed)
        self.refresh()

    # Choices -------------------------------------------------------------

    def _refill(self, combo: QComboBox, first: str, items: list[tuple[str, object]]) -> None:
        current = combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(first, _ANY)
        for text, data in items:
            combo.addItem(text, data)
        index = combo.findData(current)
        combo.setCurrentIndex(max(index, 0))
        combo.blockSignals(False)

    def reload_choices(self) -> None:
        db = self.app.db
        self._refill(self.customer, "Alle Kunden", [(c["name"], c["id"]) for c in db.customers()])
        self._customer_changed()
        self._refill(
            self.campaign, "Alle Kampagnen",
            [(f"{c['title']} ({c['started_at'][:10]})", c["id"]) for c in self.app.service.campaigns()],
        )
        keys = db.query(
            "SELECT key, min(label) AS label FROM measured_values WHERE base_value IS NOT NULL"
            " GROUP BY key ORDER BY label"
        )
        self._refill(self.value_key, "Beliebiger Messwert", [(k["label"], k["key"]) for k in keys])

    def _customer_changed(self) -> None:
        customer = self.customer.currentData()
        assets = self.app.db.assets(customer) if customer else self.app.db.assets()
        self._refill(self.asset, "Alle Anlagen", [(a["name"], a["id"]) for a in assets])

    # Results -------------------------------------------------------------

    def _bound(self, field: QLineEdit) -> Quantity | None:
        quantity = Quantity.parse(field.text().strip())
        return quantity if quantity and quantity.base_value is not None else None

    def current_filter(self) -> MeasurementFilter:
        low, high = self._bound(self.value_min), self._bound(self.value_max)
        return MeasurementFilter(
            text=self.text.text(),
            customer_id=self.customer.currentData(),
            asset_id=self.asset.currentData(),
            campaign_id=self.campaign.currentData(),
            function=self.function.currentData(),
            verdict=self.verdict.currentData(),
            date_from=self.date_from.date().toPython() if self.use_from.isChecked() else None,
            date_to=self.date_to.date().toPython() if self.use_to.isChecked() else None,
            value_key=self.value_key.currentData(),
            value_min=low.base_value if low else None,
            value_max=high.base_value if high else None,
            value_unit=(high or low).base_unit if (high or low) else "",
            has_photo=True if self.photos_only.isChecked() else None,
        )
