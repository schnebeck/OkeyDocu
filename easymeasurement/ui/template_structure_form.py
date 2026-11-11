# EasyMeasurement - easymeasurement/ui/template_structure_form.py
# The property form of the block that lists measurements by the structure of the installation.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel

from ..l10n import tr
from ..reporting.structure import ORDERS


class TemplateStructureForm:
    def _form_structure(self, block: dict, form: QFormLayout) -> None:
        about = QLabel(tr(
            "Each element of the installation with measurements becomes a section. Every"
            " measured quantity in it first states what its measurements share: settings,"
            " conditions and limits."))
        about.setWordWrap(True)
        form.addRow(about)
        order = QComboBox()
        for key, text in ORDERS.items():
            order.addItem(tr(text), key)
        order.setCurrentIndex(max(order.findData(block.get("order", "place")), 0))

        def order_changed() -> None:
            block["order"] = order.currentData()
            self._changed()

        order.currentIndexChanged.connect(order_changed)
        form.addRow(tr("Order"), order)
        features = QCheckBox(tr("Show what each element is: identifier, maker, features, remark"))
        features.setChecked(block.get("features", True))

        def features_changed(checked: bool) -> None:
            block.pop("features", None)
            if not checked:
                block["features"] = False
            self._changed()

        features.toggled.connect(features_changed)
        form.addRow(features)
        many = block.setdefault("many", {})
        summary = QCheckBox(tr("Show min and max row"))
        summary.setChecked(many.get("summary", True))
        summary.toggled.connect(lambda v: (many.__setitem__("summary", v), self._changed()))
        form.addRow(summary)
        self.structure_order, self.structure_summary = order, summary
