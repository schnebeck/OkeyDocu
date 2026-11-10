# EasyMeasurement - tests/test_campaign_edit.py
# Changing title and installation of an open campaign, and the context menu of the campaign list.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.store import CampaignClosed
from easymeasurement.ui.campaign_edit import TESTER, CampaignEditOverlay


@pytest.fixture
def places(app):
    customer = app.db.add_customer("Muster AG")
    hall = app.db.add_asset(customer, "installation", "Halle")
    press = app.db.add_asset(customer, "machine", "Presse", parent_id=hall)
    cabinet = app.db.add_asset(customer, "measuring_point", "Schrank", parent_id=press)
    other = app.db.add_asset(customer, "machine", "Kompressor")
    return {"hall": hall, "press": press, "cabinet": cabinet, "other": other}


def _measure_at(app, campaign, asset_id):
    value = ResultValue("riso", "RISO", Quantity.parse("2MΩ"), Verdict.PASSED, ">1MΩ", "")
    app.service.add_measurement(campaign, "riso", [value], datetime(2026, 5, 4, 9), Verdict.PASSED,
                                asset_id=asset_id)


# The rule --------------------------------------------------------------------


def test_the_title_changes(app, places):
    campaign = app.service.create(places["press"], "Alt", "Prüfer")
    app.service.update_campaign(campaign, "  Neu  ", places["press"])
    assert app.service.campaign(campaign)["title"] == "Neu"


def test_a_campaign_needs_a_title(app, places):
    campaign = app.service.create(places["press"], "Alt", "Prüfer")
    with pytest.raises(ValueError):
        app.service.update_campaign(campaign, " ", places["press"])


def test_a_closed_campaign_keeps_its_title(app, places):
    campaign = app.service.create(places["press"], "Alt", "Prüfer")
    app.service.close(campaign)
    with pytest.raises(CampaignClosed):
        app.service.update_campaign(campaign, "Neu", places["press"])


def test_the_installation_may_grow_around_what_was_measured(app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    _measure_at(app, campaign, places["cabinet"])
    app.service.update_campaign(campaign, "Prüfung", places["hall"])
    assert app.service.campaign(campaign)["asset_id"] == places["hall"]


def test_nothing_measured_may_end_up_outside_the_installation(app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    _measure_at(app, campaign, places["cabinet"])
    app.service.add_comment(campaign, "Schlüssel beim Hausmeister", asset_id=places["press"])
    assert app.service.misplaced(campaign, places["other"]) == 2
    with pytest.raises(ValueError):
        app.service.update_campaign(campaign, "Prüfung", places["other"])


def test_without_places_any_installation_will_do(app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    _measure_at(app, campaign, None)
    app.service.update_campaign(campaign, "Prüfung", places["other"])
    assert app.service.campaign(campaign)["asset_id"] == places["other"]


# The overlay -----------------------------------------------------------------


def test_the_overlay_says_why_the_installation_cannot_change(qtbot, app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    _measure_at(app, campaign, places["cabinet"])
    overlay = CampaignEditOverlay(app, app.service.campaign(campaign))
    qtbot.addWidget(overlay)
    overlay.asset.setCurrentIndex(overlay.asset.findData(places["other"]))
    assert not overlay.ok_button.isEnabled()
    assert "1 Messungen oder Dateien" in overlay.hint.text()
    overlay.asset.setCurrentIndex(overlay.asset.findData(places["hall"]))
    assert overlay.ok_button.isEnabled()


def test_the_way_to_the_tester_keeps_a_new_title(qtbot, app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    overlay = CampaignEditOverlay(app, app.service.campaign(campaign))
    qtbot.addWidget(overlay)
    overlay.title.setText("Neu")
    overlay._follow(TESTER)
    assert overlay.accepted and overlay.follow_up == TESTER


def test_editing_from_the_header_renames_everywhere(window, app, places, monkeypatch):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    assert page.header.edit_button.isVisible()

    def rename(overlay):
        overlay.title.setText("Wiederholungsprüfung")
        return 1

    monkeypatch.setattr(CampaignEditOverlay, "exec", rename)
    page.header.edit_button.click()
    assert page.header.title.text() == "Wiederholungsprüfung"
    assert page.list.items[campaign].text(0).startswith("Wiederholungsprüfung")


def test_a_closed_campaign_offers_no_editing(window, app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    app.service.close(campaign)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    assert not page.header.edit_button.isVisible()
    assert page.edit_action not in page.menu_actions()
    assert page.report_action in page.menu_actions()


# The context menu --------------------------------------------------------------


def test_the_context_menu_offers_what_an_open_campaign_allows(window, app, places):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    page = window.campaign
    page.refresh()
    menu = page.campaign_menu(campaign)
    shown = [action.text() for action in menu.actions() if not action.isSeparator()]
    assert page.campaign_id == campaign
    assert shown[:3] == ["Kampagne bearbeiten …", "Prüfer ändern …", "Messplan zuweisen …"]
    assert "Protokoll bestätigen …" in shown
    assert "Protokoll erstellen …" not in shown


def test_a_right_click_on_a_campaign_asks_for_its_menu(window, app, places, qtbot):
    campaign = app.service.create(places["press"], "Prüfung", "Prüfer")
    campaigns = window.campaign.list
    campaigns.refresh()
    campaigns.menu_requested.disconnect()  # the real menu would wait for a choice
    position = campaigns.tree.visualItemRect(campaigns.items[campaign]).center()
    with qtbot.waitSignal(campaigns.menu_requested) as signal:
        campaigns._context_menu(position)
    assert signal.args[0] == campaign
