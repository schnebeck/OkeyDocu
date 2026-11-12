# EasyMeasurement - tests/test_plan_run_ui.py
# Test plans at the side of a campaign: run one in the middle, pause, end or remove it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from easymeasurement.campaign.plan import parse_plan
from easymeasurement.ui import campaign_plans
from easymeasurement.ui.guided_pages import ReasonOverlay

PLAN = parse_plan("""
key: sight
title: Sichtprüfung
released: true
steps:
  - {key: b, kind: check, title: "Abdeckung vorhanden?"}
  - {key: c, kind: check, title: "Schäden sichtbar?", expected: "no"}
""")


@pytest.fixture
def page(window, app, asset):
    campaign = app.service.create(asset, "T", "Anna", PLAN)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return page


def test_a_plan_is_listed_and_the_middle_shows_the_measurements(page):
    assert page.plan_list.list.count() == 1
    assert "0 von 2 erledigt" in page.plan_list.list.item(0).text()
    assert page.middle.currentWidget() is page.work


def test_running_takes_the_middle_and_pausing_gives_it_back(page, app):
    page.plan_list.run_button.click()
    assert page.middle.currentWidget() is page.plan_run
    assert not page.plan_list.run_button.isEnabled()
    page.guided.check_page.buttons["yes"].click()
    page.plan_run.pause_button.click()
    assert page.middle.currentWidget() is page.work
    assert page.plan_list.run_button.text() == "Fortsetzen"
    page.plan_list.run_button.click()
    assert page.guided.steps.currentRow() == 1  # goes on at the first open step


def test_ending_skips_the_rest_with_the_reason(page, app, monkeypatch):
    page.plan_list.run_button.click()

    def give_reason(overlay):
        overlay.reason.setPlainText("Anlage in Betrieb")
        return 1

    monkeypatch.setattr(ReasonOverlay, "exec", give_reason)
    page.plan_run.end_button.click()
    notes = {row["note"] for row in app.service.steps(page.campaign_id)}
    assert notes == {"Anlage in Betrieb"}
    assert page.middle.currentWidget() is page.work
    assert "erledigt" == page.plan_list.list.item(0).text().split("\n")[1]


def test_removing_asks_and_takes_the_plan(page, app, monkeypatch):
    asked = []
    monkeypatch.setattr(campaign_plans, "ask_remove",
                        lambda parent, block, booked: asked.append(booked) or True)
    page.plan_list.run_button.click()
    page.guided.check_page.buttons["yes"].click()
    page.plan_list.remove_button.click()
    assert asked == [1]
    assert app.service.steps(page.campaign_id) == []
    assert app.service.measurements(page.campaign_id) == []
    assert not page.plan_section.isVisible()
    assert page.middle.currentWidget() is page.work
