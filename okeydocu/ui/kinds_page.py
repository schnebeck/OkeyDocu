# OkeyDocu - okeydocu/ui/kinds_page.py
# Settings for the kinds of structure elements: name, picture, counterparts, interval, features.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..l10n import plural, tr
from ..store.kinds import Kind
from .board import GutterSplitter
from .campaign_items import heading
from .common import ROW_ID, AppContext
from .kind_catalog import KindCatalog, element_icon, icon_names, icon_text
from .kind_features import FeatureTable
from .kind_removal import RemoveKindOverlay


class KindsPage(QWidget):
    """Every change is stored at once; the list says how many elements use each kind."""

    changed = Signal()

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.kinds = QListWidget()
        self.kinds.setIconSize(QSize(24, 24))
        self.kinds.currentItemChanged.connect(lambda item, _: self._show(item))
        add = QPushButton(tr("New kind"))
        add.clicked.connect(self._add)
        self.remove_button = QPushButton(tr("Delete …"))
        self.remove_button.clicked.connect(self._remove)
        buttons = QHBoxLayout()
        buttons.addWidget(add)
        buttons.addWidget(self.remove_button)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(heading(tr("Structure kinds"), 11))
        left_layout.addWidget(self.kinds, 1)
        left_layout.addLayout(buttons)

        self.label = QLineEdit()
        self.label.editingFinished.connect(self._save)
        self.icon = QComboBox()
        self.icon.setIconSize(QSize(20, 20))
        for name in sorted(icon_names(), key=lambda n: icon_text(n).casefold()):
            self.icon.addItem(element_icon(name), icon_text(name), name)
        self.icon.activated.connect(lambda _: self._save())
        self.izytron = QSpinBox(maximum=9999)
        self.izytron.setSpecialValueText(tr("none", context="type code"))
        self.izytron.editingFinished.connect(self._save)
        self.interval = QSpinBox(maximum=240, suffix=" " + tr("months"))
        self.interval.setSpecialValueText(tr("no repetition"))
        self.interval.editingFinished.connect(self._save)
        self.features = FeatureTable()
        self.features.edited.connect(self._save)
        self.usage = QLabel()
        self.usage.setEnabled(False)
        form = QFormLayout()
        form.addRow(tr("Label"), self.label)
        form.addRow(tr("Icon"), self.icon)
        form.addRow(tr("IZYTRON type code"), self.izytron)
        form.addRow(tr("Inspection interval"), self.interval)
        self.editor = QWidget()
        right = QVBoxLayout(self.editor)
        right.setContentsMargins(0, 0, 0, 0)
        right.addLayout(form)
        right.addWidget(heading(tr("Features"), 11))
        right.addWidget(self.features, 1)
        right.addWidget(self.usage)

        splitter = GutterSplitter(objectName="kinds")
        splitter.addWidget(left)
        splitter.addWidget(self.editor)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 520])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)
        self.refresh()

    def refresh(self, select: str | None = None) -> None:
        keep = select or self.current_key()
        catalog = KindCatalog(self.app.db)
        self.kinds.blockSignals(True)
        self.kinds.clear()
        for kind in sorted(catalog.all, key=lambda k: k.label.casefold()):
            used = self.app.db.kind_usage(kind.key)
            usage = tr("{count} in use", count=used) if used else tr("unused")
            text = f"{kind.label}\n{usage}"
            item = QListWidgetItem(catalog.icon(kind.key), text)
            item.setData(ROW_ID, kind.key)
            self.kinds.addItem(item)
            if kind.key == keep:
                self.kinds.setCurrentItem(item)
        self.kinds.blockSignals(False)
        if self.kinds.currentItem() is None and self.kinds.count():
            self.kinds.setCurrentRow(0)
        self._show(self.kinds.currentItem())

    def current_key(self) -> str | None:
        item = self.kinds.currentItem()
        return item.data(ROW_ID) if item is not None else None

    def _show(self, item) -> None:
        kind = self.app.db.kind(item.data(ROW_ID)) if item is not None else None
        self.editor.setEnabled(kind is not None)
        self.remove_button.setEnabled(kind is not None)
        if kind is None:
            return
        self.label.setText(kind.label)
        self.icon.setCurrentIndex(max(self.icon.findData(kind.icon), 0))
        self.izytron.setValue(kind.izytron_type or 0)
        self.interval.setValue(kind.interval_months)
        self.features.show_features(kind.features, self.app.db.choice_lists())
        used = self.app.db.kind_usage(kind.key)
        if used:
            usage = plural(used, "{count} element is of this kind.",
                           "{count} elements are of this kind.")
        else:
            usage = tr("No element is of this kind.")
        self.usage.setText(usage)

    def _save(self) -> None:
        key = self.current_key()
        stored = self.app.db.kind(key) if key else None
        if stored is None:
            return
        kind = replace(
            stored, label=self.label.text().strip() or stored.label, icon=self.icon.currentData(),
            izytron_type=self.izytron.value() or None,
            interval_months=self.interval.value(), features=self.features.features(),
        )
        if kind != stored:
            self.app.db.save_kind(kind)
            item = self.kinds.currentItem()
            item.setIcon(element_icon(kind.icon))
            item.setText(kind.label + "\n" + item.text().split("\n", 1)[1])
            self.changed.emit()

    def _add(self) -> None:
        label = tr("New kind")
        key = self.app.db.new_kind_key(label)
        self.app.db.save_kind(Kind(key, label))
        self.refresh(select=key)
        self.label.setFocus()
        self.label.selectAll()
        self.changed.emit()

    def _remove(self) -> None:
        key = self.current_key()
        if key is None:
            return
        overlay = RemoveKindOverlay(self.app, key, self.window())
        if overlay.exec():
            self.app.db.delete_kind(key, overlay.replacement())
            self.refresh()
            self.changed.emit()
