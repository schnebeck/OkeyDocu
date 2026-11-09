# EasyMeasurement - easymeasurement/ui/campaign_dialog.py
# The dialog that starts a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QFormLayout, QLineEdit

from ..devices import FoundInstrument, find_instruments
from .common import AppContext
from .kind_catalog import KindCatalog
from .overlay import Overlay
from .users import UserChoice


def fill_assets(combo: QComboBox, app: AppContext) -> None:
    """In tree order and indented, so the place of an element shows in the list."""
    combo.clear()
    catalog = KindCatalog(app.db)
    for customer in app.db.customers():
        below: dict[int | None, list] = {}
        for asset in app.db.assets(customer["id"]):
            below.setdefault(asset["parent_id"], []).append(asset)

        def add(parent, depth: int) -> None:
            for asset in below.get(parent, ()):
                indent = "\u2003" * depth
                text = (f"{customer['name']} – {asset['name']}" if depth == 0
                        else f"{indent}{asset['name']}")
                combo.addItem(catalog.icon(asset["kind"]), text, asset["id"])
                combo.setItemData(combo.count() - 1, catalog.label(asset["kind"]),
                                  Qt.ItemDataRole.ToolTipRole)
                add(asset["id"], depth + 1)

        add(None, 0)


class CampaignDialog(Overlay):
    """New campaign, with or without a plan.

    A plan guides the operator step by step; without one, measurements simply
    collect in a list. The instrument is chosen by name: how it connects is not
    a question here. Whatever can be suggested is, so a campaign usually starts
    with one key.
    """

    def __init__(self, app: AppContext, parent=None, plans: list | None = None):
        super().__init__("Neue Kampagne", parent)
        self.ok_button.setText("Kampagne starten")
        self.plan = QComboBox()
        for plan in plans or ():
            self.plan.addItem(plan.label, plan)
        self.plan.addItem("Ohne Plan", None)
        self.asset = QComboBox()
        fill_assets(self.asset, app)
        self.tester = UserChoice(app, app.service.last_user_id())
        self.title = QLineEdit(f"Prüfung vom {date.today():%d.%m.%Y}")
        self.source = QComboBox()
        self._fill_sources()
        self.plan.currentIndexChanged.connect(self._fill_sources)
        self.title.textChanged.connect(self._update)
        self.tester.changed.connect(self._update)
        # A cable can be plugged in while this is open.
        self._watch = QTimer(self, interval=2000)
        self._watch.timeout.connect(self._fill_sources)
        self._watch.start()
        form = QFormLayout()
        form.addRow("Anlage", self.asset)
        form.addRow("Prüfer", self.tester)
        form.addRow("Messplan", self.plan)
        form.addRow("Titel", self.title)
        form.addRow("Messgerät", self.source)
        self.body.addLayout(form)
        self._update()

    def first_field(self):
        return self.title

    def _sources(self) -> list[FoundInstrument | None]:
        """Real instruments first, so the one at hand is already chosen.

        A plan's steps are measured, so it needs an instrument, if only a
        simulated one. Without a plan values can also be typed in, shown as None.
        """
        sources: list[FoundInstrument | None] = list(find_instruments())
        if self.plan.currentData() is None:
            sources.append(None)
        else:
            sources.append(FoundInstrument("simulator", "Simulator (Zufallswerte)"))
        return sources

    def _fill_sources(self) -> None:
        sources = self._sources()
        if sources == [self.source.itemData(i) for i in range(self.source.count())]:
            return
        chosen = self.source.currentData()
        self.source.blockSignals(True)
        self.source.clear()
        for source in sources:
            self.source.addItem(source.label if source else "Manuelle Eingabe", source)
        kept = chosen is not None and chosen in sources
        self.source.setCurrentIndex(sources.index(chosen) if kept else 0)
        self.source.blockSignals(False)

    def _update(self) -> None:
        missing = []
        if self.asset.currentData() is None:
            missing.append("eine Anlage")
        if self.tester.current_id() is None:
            missing.append("ein Prüfer")
        if not self.title.text().strip():
            missing.append("ein Titel")
        self.ok_button.setEnabled(not missing)
        self.hint.setText(f"Es fehlt noch {' und '.join(missing)}." if missing else "")

    def _leave(self) -> None:
        self._watch.stop()
        super()._leave()
