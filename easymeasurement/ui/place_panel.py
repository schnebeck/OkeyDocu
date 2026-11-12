# EasyMeasurement - easymeasurement/ui/place_panel.py
# The chosen element in the side panel: what is known about it and what suits measuring it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A feature holding a value of a choice list tells its facts, curve and help in a tip, as in
the element's form. Below the features stand the measurements those values call for; the
tip of each names the values behind it and what to mind."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..l10n import tr
from .choice_tips import text_tip
from .common import AppContext
from .dashboard_card import dim
from .element_form import TEXTS, interval_text
from .kind_catalog import KindCatalog
from .place_files import PlaceFiles
from .rich_tip import install_tip
from .suited_methods import context_of, method_tip, suited

TIPPED = Qt.CursorShape.WhatsThisCursor  # tells the mouse that a tip waits


def _clear(layout: QLayout) -> None:
    while layout.count():
        widget = layout.takeAt(0).widget()
        if widget is not None:
            widget.hide()  # gone at once; deleting waits for the event loop
            widget.deleteLater()


class PlacePanel(QWidget):
    """What is known about the chosen element; empty features are left out."""

    properties_requested = Signal(int)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.asset_id: int | None = None
        self.icon = QLabel()
        self.name = QLabel()
        self.name.setWordWrap(True)
        font = self.name.font()
        font.setBold(True)
        self.name.setFont(font)
        self.kind = dim(QLabel())
        self.details = QWidget()
        self.grid = QGridLayout(self.details)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(1)
        self.grid.setColumnStretch(1, 1)
        self.suited_title = QLabel(tr("Suited measurements"))
        self.suited_title.setFont(font)
        self.suited = QWidget()
        self.suited_lines = QVBoxLayout(self.suited)
        self.suited_lines.setContentsMargins(0, 0, 0, 0)
        self.suited_lines.setSpacing(1)
        self.edit_button = QPushButton(tr("Properties …"))
        self.edit_button.clicked.connect(lambda: self.properties_requested.emit(self.asset_id))
        self.files = PlaceFiles(app, tr("this location"))
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(self.name)
        names.addWidget(self.kind)
        names.addStretch(1)
        top = QHBoxLayout()
        top.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        top.addLayout(names, 1)
        top.addWidget(self.edit_button, 0, Qt.AlignmentFlag.AlignTop)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        for widget in (self.details, self.suited_title, self.suited, self.files):
            layout.addWidget(widget)
        layout.addStretch(1)

    def show_element(self, asset_id: int | None, campaign_id: int | None, editable: bool) -> None:
        self.asset_id = asset_id
        row = self.app.db.asset(asset_id) if asset_id is not None else None
        self.setVisible(row is not None)
        if row is None:
            self.files.show_target(None)
            return
        catalog = KindCatalog(self.app.db)
        kind = catalog.by_key.get(row["kind"])
        self.icon.setPixmap(catalog.icon(row["kind"]).pixmap(32, 32))
        self.name.setText(row["name"])
        self.kind.setText(catalog.label(row["kind"]))
        self._show_details(row, kind)
        self.files.target_name = row["name"]
        self.files.show_target(campaign_id, editable, asset_id=asset_id)

    def detail_texts(self) -> list[str]:
        """The texts of the details as they read, name and value in turn."""
        return [self.grid.itemAt(i).widget().text() for i in range(self.grid.count())]

    def suited_texts(self) -> list[str]:
        return [self.suited_lines.itemAt(i).widget().text()
                for i in range(self.suited_lines.count())]

    def _show_details(self, row, kind) -> None:
        _clear(self.grid)
        values = self.app.db.asset_features(row["id"])
        features = kind.features if kind else ()
        context = context_of(self.app.db, row["id"], values)
        lists = self.app.db.choice_lists()
        for key in ("identifier", "manufacturer", "type", "serial_no", "comment"):
            if row[key]:
                self._add_line(tr(TEXTS[key]), row[key])
        for feature in features:
            text = values.get(feature.key, "")
            if not text:
                continue
            shown = self._add_line(feature.label, f"{text} {feature.unit}".strip())
            chosen = lists.get(feature.choice_list or "")
            if chosen is not None and text_tip(chosen, text) is not None:
                install_tip(shown, lambda _, c=chosen, t=text: text_tip(c, t, context))
                shown.setCursor(TIPPED)
        months = row["interval_months"]
        if months is None and kind is not None:
            months = kind.interval_months
        if months:
            self._add_line(tr("Inspection interval"), interval_text(months))
        self.details.setVisible(self.grid.count() > 0)
        self._show_suited(suited(features, lists, values))

    def _add_line(self, name: str, text: str) -> QLabel:
        line = self.grid.count() // 2  # two labels a line; a cleared grid starts at the top
        label = dim(QLabel(name))
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        shown = QLabel(text)
        shown.setWordWrap(True)
        shown.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.grid.addWidget(label, line, 0)
        self.grid.addWidget(shown, line, 1)
        return shown

    def _show_suited(self, found: dict) -> None:
        _clear(self.suited_lines)
        for function, reasons in found.items():
            tip = method_tip(function, reasons)
            line = QLabel(f"• {tip.title}")
            line.setWordWrap(True)
            line.setCursor(TIPPED)
            install_tip(line, lambda _, t=tip: t)
            self.suited_lines.addWidget(line)
        self.suited_title.setVisible(bool(found))
        self.suited.setVisible(bool(found))
