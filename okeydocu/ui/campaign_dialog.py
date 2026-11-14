# OkeyDocu - okeydocu/ui/campaign_dialog.py
# The dialog that starts a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLineEdit

from ..campaign.editing import CONTACT_COLUMNS
from ..devices import FoundInstrument, find_instruments
from ..l10n import day, tr
from .campaign_order import OrderFields
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

    def __init__(self, app: AppContext, parent=None, plans: list | None = None,
                 repeat_of: int = 0):
        super().__init__(tr("New campaign"), parent)
        self.app = app
        # The order to repeat; without one, the last confirmed of the installation is offered.
        self.repeat_of = app.service.campaign(repeat_of) if repeat_of else None
        self.ok_button.setText(tr("Start campaign"))
        self.plan = QComboBox()
        for plan in plans or ():
            self.plan.addItem(plan.label, plan)
        self.plan.addItem(tr("Without plan"), None)
        self.template = QComboBox()
        self.template.addItem(tr("Without template"), None)
        for kept in app.service.templates():
            self.template.addItem(kept.title, kept.key)
        self.template.currentIndexChanged.connect(lambda _: self._template_chosen())
        self.asset = QComboBox()
        fill_assets(self.asset, app)
        self.tester = UserChoice(app, app.service.last_user_id())
        self.title = QLineEdit(tr("Inspection of {day}", day=day(date.today())))
        # The usual case: what was recorded last time is the list to take again.
        self.repeat = QCheckBox()
        self.previous = None
        self.repeat.toggled.connect(self._repeat_toggled)
        self.asset.currentIndexChanged.connect(self._offer_repeat)
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
        form.addRow(tr("Installation"), self.asset)
        form.addRow(tr("Inspector"), self.tester)
        form.addRow("", self.repeat)
        form.addRow(tr("Test plan"), self.plan)
        if self.template.count() > 1:
            form.addRow(tr("Campaign template"), self.template)
        form.addRow(tr("Title"), self.title)
        form.addRow(tr("Instrument"), self.source)
        self.order = OrderFields(form, {})
        self.asset.currentIndexChanged.connect(self._suggest_contact)
        self.body.addLayout(form)
        self._suggest_contact()
        self._offer_repeat()
        self._update()

    def _offer_repeat(self) -> None:
        """An inspection without a single point leaves nothing to repeat."""
        asset = self.asset.currentData()
        self.previous = self._chosen_order(asset)
        if self.previous is None and asset is not None:
            self.previous = self.app.service.last_closed(asset)
        count = 0
        if self.previous is not None:
            count = self.app.db.one("SELECT count(*) FROM measurements WHERE campaign_id=?",
                                    self.previous["id"])[0]
        if not count:
            self.previous = None
        if self.previous is not None:
            closed = datetime.fromisoformat(self.previous["closed_at"])
            self.repeat.setText(tr("Repeat like the inspection of {day} ({count} points)",
                                   day=day(closed), count=count))
        self.repeat.setVisible(self.previous is not None)
        self.repeat.setChecked(self.previous is not None)

    def _suggest_contact(self) -> None:
        """The contact of the order repeated, or else the customer's last one: the likeliest
        to ask again."""
        asset = self.asset.currentData()
        previous = self._chosen_order(asset)
        if previous is None and asset is not None:
            previous = self.app.service.last_contact(asset)
        if previous is not None:
            previous = {key: previous[key] for key in CONTACT_COLUMNS}
        self.order.fill(dict(previous) if previous else dict.fromkeys(CONTACT_COLUMNS, ""))

    def _chosen_order(self, asset):
        """The order to repeat, while its installation is the one chosen."""
        chosen = self.repeat_of
        return chosen if chosen is not None and chosen["asset_id"] == asset else None

    def _repeat_toggled(self, on: bool) -> None:
        """A repeat inspection brings its own list; a plan or template beside it would lead
        elsewhere."""
        if on:
            self.plan.setCurrentIndex(self.plan.findData(None))
            self.template.setCurrentIndex(0)
        self.plan.setEnabled(not on and self.template.currentData() is None)

    def _template_chosen(self) -> None:
        """A template brings its own points, like a repeat inspection."""
        chosen = self.template.currentData() is not None
        if chosen:
            self.repeat.setChecked(False)
            self.plan.setCurrentIndex(self.plan.findData(None))
        self.plan.setEnabled(not chosen and not self.repeat.isChecked())

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
            sources.append(FoundInstrument("simulator", tr("Simulator (random values)")))
        return sources

    def _fill_sources(self) -> None:
        sources = self._sources()
        if sources == [self.source.itemData(i) for i in range(self.source.count())]:
            return
        chosen = self.source.currentData()
        self.source.blockSignals(True)
        self.source.clear()
        for source in sources:
            self.source.addItem(source.label if source else tr("Manual entry"), source)
        kept = chosen is not None and chosen in sources
        self.source.setCurrentIndex(sources.index(chosen) if kept else 0)
        self.source.blockSignals(False)

    def _update(self) -> None:
        missing = []
        if self.asset.currentData() is None:
            missing.append(tr("an installation"))
        if self.tester.current_id() is None:
            missing.append(tr("an inspector"))
        if not self.title.text().strip():
            missing.append(tr("a title"))
        self.ok_button.setEnabled(not missing)
        listed = missing[0] if missing else ""
        for item in missing[1:]:
            listed = tr("{items} and {last}", items=listed, last=item)
        self.hint.setText(tr("Still missing: {items}.", items=listed) if missing else "")

    def _leave(self) -> None:
        self._watch.stop()
        super()._leave()
