# EasyMeasurement - tests/test_dashboard.py
# The start screen: recent campaigns, search, next steps, and the tiles to everything set up once.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date, datetime, timedelta

from PySide6.QtCore import Qt

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.ui.dashboard import CLOSED_SHOWN, OPEN_SHOWN
from easymeasurement.ui.dashboard_card import (
    MAKE_REPORT,
    OPEN_REPORT,
    RESUME,
    SHOW,
    attention,
    when_text,
)
from easymeasurement.ui.dashboard_tiles import MASTER_DATA, PLANS

from .workspace_helpers import start, with_asset

T0 = datetime(2026, 5, 4, 9, 0)


def _measure(app, campaign, minutes, verdict=Verdict.PASSED):
    value = ResultValue("riso", "RISO", Quantity.parse("2.0MΩ"), verdict, ">1MΩ", "")
    app.service.add_measurement(campaign, "riso", [value], T0 + timedelta(minutes=minutes), verdict)


def _campaigns(app, count):
    asset = app.db.add_asset(app.db.add_customer("Nordwerk AG", city="Bremen"), "machine", "Presse")
    return [app.service.create(asset, f"Prüfung {n}", "B. Prüfer") for n in range(count)]


def _home(window):
    window.campaign.refresh()
    return window.campaign.home


# Figures ---------------------------------------------------------------------


def test_a_summary_counts_measurements_failures_and_steps(app):
    campaign, = _campaigns(app, 1)
    _measure(app, campaign, 0)
    _measure(app, campaign, 1, Verdict.FAILED)
    summary, = app.service.summaries()
    assert (summary.measured, summary.failed, summary.steps) == (2, 1, 0)
    assert (summary.customer, summary.city, summary.asset) == ("Nordwerk AG", "Bremen", "Presse")
    assert summary.active_at >= T0 + timedelta(minutes=1)


def test_the_campaign_measured_in_last_comes_first(app):
    first, second = _campaigns(app, 2)
    _measure(app, first, 60 * 24 * 365 * 5)  # far ahead of the start of the other one
    assert [s.id for s in app.service.summaries()][:2] == [first, second]


def test_searching_needs_every_word():
    from easymeasurement.campaign.overview import CampaignSummary
    summary = CampaignSummary(1, "Prüfung Halle", True, "manual", "Anna", "", "Nordwerk AG",
                              "Bremen", "Presse", 0, 0, 0, 0, 0, 0, T0)
    assert summary.matches(["bremen", "presse"])
    assert not summary.matches(["bremen", "köln"])


def test_days_are_named_near_today():
    today = date(2026, 5, 4)
    assert when_text(T0, today) == "heute 09:00"
    assert when_text(T0, today + timedelta(days=1)) == "gestern 09:00"
    assert when_text(T0, today + timedelta(days=9)) == "04.05.2026"


# The screen ------------------------------------------------------------------


def test_only_the_campaigns_worked_on_last_are_shown(window, app):
    _campaigns(app, OPEN_SHOWN + 2)
    home = _home(window)
    assert len(home.cards) == OPEN_SHOWN
    assert f"von {OPEN_SHOWN + 2}" in home.open_section.heading.text()
    assert home.search.isVisibleTo(home)


def test_open_and_closed_measurements_stand_apart(window, app):
    ids = _campaigns(app, CLOSED_SHOWN + 2)
    for campaign in ids[1:]:
        app.service.close(campaign)
    home = _home(window)
    assert [card.summary.id for card in home.open_section.cards] == [ids[0]]
    assert len(home.closed_section.cards) == CLOSED_SHOWN
    assert home.open_section.heading.text() == "Offene Messungen"


def test_with_few_campaigns_there_is_nothing_to_search(window, app):
    _campaigns(app, 2)
    assert not _home(window).search.isVisibleTo(window.campaign.home)


def test_searching_looks_at_every_campaign_and_return_opens_the_first(window, app):
    ids = _campaigns(app, OPEN_SHOWN + 2)
    home = _home(window)
    home.search.setText("Prüfung 0")
    assert [card.summary.id for card in home.cards] == [ids[0]]
    home.search.returnPressed.emit()
    assert window.campaign.campaign_id == ids[0]


def test_a_search_without_result_says_so(window, app):
    _campaigns(app, OPEN_SHOWN + 1)
    home = _home(window)
    home.search.setText("nirgends")
    assert home.cards == []
    assert "nirgends" in home.empty.text()


def test_the_card_names_the_next_step(window, app):
    open_one, closed_one = _campaigns(app, 2)
    app.service.close(closed_one)
    cards = {card.summary.id: card for card in _home(window).cards}
    assert (cards[open_one].action, cards[open_one].button.text()) == (SHOW, "Öffnen")
    assert cards[closed_one].action == MAKE_REPORT
    assert attention(cards[closed_one].summary) == ["Noch kein Protokoll erstellt"]


def test_making_the_missing_report_is_one_click(window, app, monkeypatch):
    campaign, = _campaigns(app, 1)
    app.service.close(campaign)
    asked = []
    monkeypatch.setattr(window.reports, "generate_for", asked.append)
    card, = _home(window).cards
    card.button.click()
    assert asked == [campaign]


def test_a_closed_campaign_with_a_report_opens_it(window, app, monkeypatch):
    from easymeasurement.reporting.template import default_template_text
    campaign, = _campaigns(app, 1)
    app.service.close(campaign)
    app.archive.generate(campaign, "Standard", default_template_text(), "de")
    opened = []
    monkeypatch.setattr("easymeasurement.ui.campaign_display.open_report",
                        lambda _, report: opened.append(report["campaign_id"]))
    card, = _home(window).cards
    assert card.action == OPEN_REPORT
    card.button.click()
    assert opened == [campaign]


def test_clicking_a_card_shows_its_campaign(window, app, qtbot):
    campaign, = _campaigns(app, 1)
    card, = _home(window).cards
    qtbot.mouseClick(card, Qt.MouseButton.LeftButton)
    assert window.campaign.campaign_id == campaign
    assert window.campaign.pages.currentWidget() is window.campaign.running


def test_the_campaign_measuring_stays_first_and_the_way_back_keeps_it(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    live = window.campaign.live_id
    _campaigns(app, OPEN_SHOWN + 1)
    window.campaign.list.home_button.click()
    home = window.campaign.home
    assert window.campaign.pages.currentWidget() is home
    assert window.campaign.session is not None  # the overview takes nothing away
    assert home.cards[0].summary.id == live
    assert home.cards[0].button.text() == "Zur Messung"
    assert window.campaign.list.current() is None


def test_a_measuring_campaign_can_be_resumed_from_its_card(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    campaign = window.campaign.live_id
    window.campaign.pause()
    window.campaign.show_home()
    card, = window.campaign.home.cards
    assert card.action == RESUME
    card.button.click()
    assert window.campaign.live_id == campaign


def test_the_tiles_lead_to_the_pages(window, app):
    tiles = _home(window).tiles
    tiles.buttons[MASTER_DATA].click()
    assert window.master_data.isVisible()
    tiles.buttons[PLANS].click()
    assert window.plan_editor.isVisible()


def test_the_tiles_tell_what_is_there(window, app):
    _campaigns(app, 1)
    figure = _home(window).tiles.buttons[MASTER_DATA].figure.text()
    assert figure == "1 Kunde, 1 Element"


def test_a_new_campaign_is_the_last_card_among_the_open_ones(window, app):
    _campaigns(app, OPEN_SHOWN + 1)
    home = _home(window)
    grid = home.open_section.grid
    assert grid.count() == OPEN_SHOWN + 1
    assert grid.itemAt(OPEN_SHOWN).widget() is home.start_button
    home.search.setText("Prüfung")
    assert home.start_button.isHidden()


def test_without_any_campaign_only_the_new_card_stands_there(window, app):
    with_asset(window, app)
    home = window.campaign.home
    assert home.cards == []
    assert home.open_section.isVisibleTo(home)
    assert home.start_button.isEnabled()
