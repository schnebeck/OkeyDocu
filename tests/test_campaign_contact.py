# EasyMeasurement - tests/test_campaign_contact.py
# The customer's department and person for a campaign, up to the report's letterhead.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from easymeasurement.reporting.context import build_context
from easymeasurement.reporting.language import speaking
from easymeasurement.reporting.nodes import Letterhead
from easymeasurement.reporting.template import default_template_text, parse_template, resolve
from easymeasurement.store import CampaignClosed
from easymeasurement.ui.campaign_edit import CampaignEditOverlay


def _client(app, campaign, language="de"):
    with speaking(language):
        nodes = resolve(parse_template(default_template_text()),
                        build_context(app.service, campaign))
    return next(node for node in nodes if isinstance(node, Letterhead)).client


@pytest.fixture
def press(app):
    customer = app.db.add_customer("Muster AG", "Hauptstraße 4", "30159", "Hannover")
    return app.db.add_asset(customer, "machine", "Presse")


def test_the_contact_belongs_to_the_campaign_and_stays_once_closed(app, press):
    campaign = app.service.create(press, "Prüfung", "Anna Prüfer")
    app.service.set_contact(campaign, "Instandhaltung", " Frau Muster ", "0511 1234-56", "")
    row = app.service.campaign(campaign)
    assert (row["department"], row["contact"], row["contact_phone"]) == (
        "Instandhaltung", "Frau Muster", "0511 1234-56")
    app.service.close(campaign)
    with pytest.raises(CampaignClosed):
        app.service.set_contact(campaign, "", "Herr Beispiel", "", "")


def test_a_new_campaign_starts_with_the_customers_last_contact(app, press):
    first = app.service.create(press, "2026", "Anna Prüfer")
    app.service.set_contact(first, "Instandhaltung", "Frau Muster", "0511 1234-56",
                             "muster@kunde.example")
    second = app.service.create(press, "2027", "Anna Prüfer")
    copied = app.service.campaign(second)
    assert (copied["department"], copied["contact"]) == ("Instandhaltung", "Frau Muster")
    other = app.db.add_asset(app.db.add_customer("Andere GmbH"), "machine", "Säge")
    assert app.service.campaign(app.service.create(other, "x", "y"))["contact"] == ""


def test_the_edit_overlay_takes_the_contact(app, window, press):
    campaign = app.service.create(press, "Prüfung", "Anna Prüfer")
    overlay = CampaignEditOverlay(app, app.service.campaign(campaign), window)
    order = overlay.order
    assert not order.expanded  # nothing but the contact person is given yet
    order.fields["department"].setText("Werkstatt")
    order.fields["contact"].setText("Herr Beispiel")
    order.fields["contact_email"].setText("beispiel@kunde.example ")
    order.fields["job_number"].setText(" V-0815")
    assert overlay._changed()
    assert order.contact_values() == ("Werkstatt", "Herr Beispiel", "", "beispiel@kunde.example")
    assert order.order_values() == ("", "V-0815")


def test_the_order_opens_where_it_holds_something(app, window, press):
    campaign = app.service.create(press, "Prüfung", "Anna Prüfer")
    app.service.set_order(campaign, "", "V-0815")
    overlay = CampaignEditOverlay(app, app.service.campaign(campaign), window)
    assert overlay.order.expanded


def test_a_new_campaign_asks_for_the_same_order_and_suggests_the_last_contact(app, window, press):
    from easymeasurement.ui.campaign_dialog import CampaignDialog

    first = app.service.create(press, "2026", "Anna Prüfer")
    app.service.set_contact(first, "", "Frau Muster", "", "")
    dialog = CampaignDialog(app, window)
    dialog.asset.setCurrentIndex(dialog.asset.findData(press))
    assert set(dialog.order.fields) == {"department", "contact", "contact_phone",
                                        "contact_email", "cost_center", "job_number"}
    assert dialog.order.fields["contact"].text() == "Frau Muster"
    assert dialog.order.order_values() == ("", "")


def test_the_letterhead_names_the_contact_only_where_there_is_one(app, press):
    campaign = app.service.create(press, "Prüfung", "Anna Prüfer")
    assert _client(app, campaign) == ["Muster AG", "Hauptstraße 4", "30159 Hannover"]
    app.service.set_contact(campaign, "", "Frau Muster", "0511 1234-56", "muster@kunde.example")
    assert _client(app, campaign)[3:] == [
        "Ansprechpartner: Frau Muster", "Telefon: 0511 1234-56", "muster@kunde.example"]
    app.service.set_contact(campaign, "Instandhaltung", "Frau Muster", "", "")
    assert _client(app, campaign)[3:] == [
        "Abteilung: Instandhaltung", "Ansprechpartner: Frau Muster"]
    assert _client(app, campaign, "en")[3:5] == [
        "Department: Instandhaltung", "Contact: Frau Muster"]


def test_cost_centre_and_job_number_stand_with_the_contractor_and_are_not_carried_on(app, press):
    app.db.save_company(name="Prüfdienst GmbH")
    first = app.service.create(press, "2026", "Anna Prüfer")
    app.service.set_order(first, " 4711 ", "V-0815")
    with speaking("de"):
        nodes = resolve(parse_template(default_template_text()), build_context(app.service, first))
    head = next(node for node in nodes if isinstance(node, Letterhead))
    assert head.contractor == ["Prüfdienst GmbH", "Kostenstelle: 4711", "Vorgangsnummer: V-0815",
                               "Prüfer: Anna Prüfer"]
    second = app.service.create(press, "2027", "Anna Prüfer")
    assert app.service.campaign(second)["cost_center"] == ""
    assert app.service.campaign(second)["job_number"] == ""
