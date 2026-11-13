# OkeyDocu - tests/test_campaign_orders.py
# An installation exists once; each campaign against it is an order with its own number and contact.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.l10n import tr
from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.ui.campaign_dialog import CampaignDialog

from .rlo_helpers import T0


def _measured(app, campaign):
    result = ResultValue("rlo", "RLO", Quantity.parse("0.10Ω"), Verdict.PASSED, "", "<1.00Ω")
    app.service.add_measurement(campaign, "rlo", [result], T0, Verdict.PASSED)


def _order(app, asset, title, job="", contact="", closed=False):
    campaign = app.service.create(asset, title, "Anna Prüfer")
    app.service.set_order(campaign, "", job)
    app.service.set_contact(campaign, "", contact, "", "")
    if closed:
        _measured(app, campaign)
        app.service.close(campaign)
    return campaign


@pytest.fixture
def orders(app, window):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    other = app.db.add_asset(app.db.add_customer("Andere GmbH"), "machine", "Säge")
    found = {
        "press": press,
        "first": _order(app, press, "Erstprüfung", "V-1", "Frau Alt", closed=True),
        "second": _order(app, press, "Wiederholung", "V-2", "Herr Neu", closed=True),
        "open": _order(app, press, "Nachmessung", "V-3"),
        "saw": _order(app, other, "Säge prüfen"),
    }
    window.campaign.refresh()
    return found


def test_orders_stand_under_their_installation_and_customer(window, orders):
    listing = window.campaign.list
    customers = [listing.tree.topLevelItem(i).text(0)
                 for i in range(listing.tree.topLevelItemCount())]
    assert customers == ["Andere GmbH", "Muster AG"]
    press = listing.items[orders["open"]].parent()
    assert press.text(0) == "Presse"
    shown = [press.child(i) for i in range(press.childCount())]
    # The open order comes first, then the newest of those confirmed.
    assert shown == [listing.items[orders[key]] for key in ("open", "second", "first")]
    first = listing.items[orders["first"]].text(0).split("\n")
    assert first[1] == "  ·  ".join([tr("Job {number}", number="V-1"), "Frau Alt"])


def test_a_folded_installation_stays_folded_until_one_of_its_orders_is_shown(window, orders):
    listing = window.campaign.list
    press = listing.items[orders["open"]].parent()
    press.setExpanded(False)
    window.campaign.refresh()
    press = listing.items[orders["open"]].parent()
    assert not press.isExpanded()
    listing.select(orders["first"])
    assert listing.items[orders["first"]].parent().isExpanded()


def test_the_header_names_the_order(window, orders):
    window.campaign.show_campaign(orders["first"])
    details = window.campaign.header.details.text()
    assert tr("Job {number}", number="V-1") in details and "Frau Alt" in details


def test_a_next_order_repeats_the_one_chosen_with_its_contact(app, window, orders):
    page = window.campaign
    page.show_campaign(orders["open"])
    assert not page.next_order_action.isEnabled()  # an open order is still being worked on
    page.show_campaign(orders["first"])
    assert page.next_order_action.isEnabled()
    dialog = CampaignDialog(app, window, repeat_of=orders["first"])
    dialog.asset.setCurrentIndex(dialog.asset.findData(orders["press"]))
    assert dialog.previous["id"] == orders["first"]  # not just the last one confirmed
    assert dialog.repeat.isChecked()
    assert dialog.order.fields["contact"].text() == "Frau Alt"
    assert dialog.order.order_values() == ("", "")  # a new order gets its own number


def test_without_a_chosen_order_the_last_confirmed_is_repeated(app, window, orders):
    dialog = CampaignDialog(app, window)
    dialog.asset.setCurrentIndex(dialog.asset.findData(orders["press"]))
    assert dialog.previous["id"] == orders["second"]


def test_the_master_data_list_the_orders_of_an_element(window, orders, monkeypatch):
    master = window.master_data
    master.refresh()
    master.select_element(orders["press"])
    shown = [master.orders.list.item(i).text().split("\n")[0]
             for i in range(master.orders.list.count())]
    assert shown == ["Nachmessung", "Wiederholung", "Erstprüfung"]
    asked = []
    monkeypatch.setattr(window.campaign, "new_campaign", lambda **given: asked.append(given))
    master.orders.new_button.click()
    assert asked == [{"asset_id": orders["press"]}]
    master.orders.open_requested.emit(orders["second"])
    assert window.campaign.campaign_id == orders["second"]
