# OkeyDocu - tests/test_campaign_plans_ui.py
# Test plans are added to and removed from a campaign at its side, whatever it started with.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.campaign.plan import parse_plan
from okeydocu.campaign.point_plans import REPEAT
from okeydocu.ui import campaign_plans

SIGHT = parse_plan("""
key: sight
title: Sichtprüfung
released: true
steps:
  - {key: b, kind: check, title: "Abdeckung vorhanden?"}
""")
LOOP = parse_plan("""
key: loop
title: Schleifenimpedanz an allen Steckdosen des Werkstattbereichs
released: true
steps:
  - {key: z, kind: check, title: "Steckdosen zugänglich?"}
""")


@pytest.fixture
def page(window, app, asset):
    campaign = app.service.create(asset, "Prüfung", "Anna")
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return page


def assign(page, monkeypatch, plan) -> None:
    class Chosen:
        def __init__(self, plans, parent):
            self.plan = type("Combo", (), {"currentData": lambda _: plan})()

        def exec(self):
            return True

    monkeypatch.setattr("okeydocu.ui.campaign_tasks.AssignPlanOverlay", Chosen)
    page.plan_list.assign_button.click()


def titles(page) -> list[str]:
    items = [page.plan_list.list.item(i) for i in range(page.plan_list.list.count())]
    return [item.text().split("\n")[0] for item in items]


def test_a_campaign_without_a_plan_offers_to_add_one(page):
    assert page.plan_section.isVisible() and page.plan_list.list.count() == 0
    assert page.plan_list.assign_button.isVisible() and page.assign_action.isEnabled()


def test_plans_are_added_one_after_the_other_and_removed_one_by_one(page, app, monkeypatch):
    assign(page, monkeypatch, SIGHT)
    assign(page, monkeypatch, LOOP)
    assert titles(page) == [SIGHT.label, LOOP.label]
    monkeypatch.setattr(campaign_plans, "ask_remove", lambda parent, block, booked: True)
    page.plan_list.list.setCurrentRow(0)
    page.plan_list.remove_button.click()
    assert titles(page) == [LOOP.label]
    assert app.service.campaign(page.campaign_id)["plan_title"] == LOOP.label


def test_a_campaign_with_points_takes_no_plan(page, app):
    app.db.execute("UPDATE campaigns SET plan_key=? WHERE id=?", REPEAT, page.campaign_id)
    page.show_campaign(page.campaign_id)
    assert not page.plan_section.isVisible()
    assert not page.assign_action.isEnabled()


def test_the_running_plan_keeps_its_progress_line_in_a_narrow_list(page, monkeypatch):
    assign(page, monkeypatch, LOOP)
    page.plan_list.run_button.click()
    item = page.plan_list.list.item(0)
    assert not item.icon().isNull() and item.text().endswith("0 von 1 erledigt")


def test_long_names_wrap_in_the_head_instead_of_widening_the_window(page, app, monkeypatch):
    for _ in range(4):
        assign(page, monkeypatch, LOOP)
    assert len(page.header.details.text()) > 250
    assert page.header.details.minimumSizeHint().width() < 400



def test_running_another_plan_sets_the_running_one_aside(page, app, monkeypatch):
    twice = parse_plan("""
key: two
title: Zwei Fragen
released: true
steps:
  - {key: a, kind: check, title: "Erste Frage?"}
  - {key: b, kind: check, title: "Zweite Frage?"}
""")
    assign(page, monkeypatch, twice)
    assign(page, monkeypatch, LOOP)
    page.plan_list.list.setCurrentRow(0)
    page.plan_list.run_button.click()
    page.guided.check_page.buttons["yes"].click()
    page.plan_list.list.setCurrentRow(1)
    assert page.plan_list.run_button.isEnabled()
    page.plan_list.run_button.click()
    first, second = app.service.plan_blocks(page.campaign_id)
    assert page.running_block() == second and first.done == 1
    page.plan_list.list.setCurrentRow(0)
    page.plan_list.run_button.click()
    assert page.running_block() == first
    assert page.guided._step()["id"] == first.step_ids[1]
