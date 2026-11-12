# EasyMeasurement - tests/test_workspace_switching.py
# Interrupting, resuming and looking at another campaign while one measures.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from .workspace_helpers import start, with_asset


def second_campaign(app, title="Andere"):
    asset = app.db.assets()[0]["id"]
    return app.service.create(asset, title, "P", None, "simulator")


def click_campaign(window, campaign):
    window.campaign.list.tree.setCurrentItem(window.campaign.list.items[campaign])


def test_interrupting_keeps_the_campaign_and_stays_on_it(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    campaign = page.campaign_id
    page.header.pause_button.click()
    assert page.session is None
    assert page.campaign_id == campaign
    assert page.current_work() is None
    assert page.header.resume_button.isVisible()
    assert "Prüfung Halle" in page.list.items[campaign].text(0)


def test_a_campaign_can_be_resumed(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    page.header.pause_button.click()
    page.header.resume_button.click()
    assert page.session is not None
    assert page.current_work() is page.free


def test_choosing_a_campaign_does_not_touch_the_instrument(window, app, monkeypatch):
    with_asset(window, app)
    campaign = second_campaign(app)
    window.campaign.refresh()
    click_campaign(window, campaign)
    assert window.campaign.campaign_id == campaign
    assert window.campaign.session is None


def test_looking_at_another_campaign_keeps_the_measurement_running(window, app, monkeypatch):
    with_asset(window, app)
    other = second_campaign(app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    live, session = page.campaign_id, page.session
    page.list.refresh()
    click_campaign(window, other)
    assert page.session is session
    assert page.live_id == live
    assert "Prüfung Halle" in page.link.text.text()


def test_reading_lands_in_the_measuring_campaign_not_the_one_on_screen(window, app, monkeypatch):
    with_asset(window, app)
    other = second_campaign(app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    live = page.campaign_id
    page.list.refresh()
    click_campaign(window, other)
    app.devices.driver(app.service.campaign(live)).simulate_measurement("u")
    assert len(app.service.measurements(live)) == 1
    assert app.service.measurements(other) == []
    assert page.values.table.rowCount() == 0
    assert "1 Messung" in page.list.items[live].text(0)


def test_instrument_actions_wait_while_another_campaign_measures(window, app, monkeypatch):
    with_asset(window, app)
    other = second_campaign(app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    assert page.clock_action.isEnabled()
    page.list.refresh()
    click_campaign(window, other)
    assert not page.clock_action.isEnabled()
    assert not page.fetch_action.isEnabled()
    assert page.resume_action.isEnabled()


def test_resuming_takes_the_instrument_over(window, app, monkeypatch):
    with_asset(window, app)
    other = second_campaign(app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    page.list.refresh()
    click_campaign(window, other)
    page.header.resume_button.click()
    assert page.live_id == other
    assert page.session.campaign_id == other


def test_double_click_resumes_an_open_campaign(window, app):
    with_asset(window, app)
    campaign = second_campaign(app)
    window.campaign.refresh()
    tree = window.campaign.list.tree
    point = tree.visualItemRect(window.campaign.list.items[campaign]).center()
    left = Qt.MouseButton.LeftButton
    QTest.mouseClick(tree.viewport(), left, pos=point)
    assert window.campaign.live_id is None  # one click only looks
    QTest.mousePress(tree.viewport(), left, pos=point)
    QTest.mouseRelease(tree.viewport(), left, pos=point)
    QTest.mouseDClick(tree.viewport(), left, pos=point)
    assert window.campaign.live_id == campaign


def test_a_new_campaign_takes_the_instrument_from_the_running_one(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    first = window.campaign.live_id
    window.campaign.new_campaign()
    assert window.campaign.live_id != first


def test_campaigns_of_the_same_name_can_be_told_apart(window, app):
    with_asset(window, app)
    first = second_campaign(app, "E-Check")
    second = second_campaign(app, "E-Check")
    app.service.add_measurement(first, "rlo", [])
    window.campaign.refresh()
    items = window.campaign.list.items
    assert items[first].text(0) != items[second].text(0)
    assert "1 Messung" in items[first].text(0)
