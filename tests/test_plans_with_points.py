# OkeyDocu - tests/test_plans_with_points.py
# A repeat inspection takes test plans beside its points; each keeps to its own rules.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.plan import parse_plan
from okeydocu.campaign.point_plans import REPEAT
from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.reporting.context import build_context

CHECKS = parse_plan("""
key: checks
title: Sichtprüfung
released: true
steps:
  - {key: a, kind: check, title: "Abdeckung vorhanden?"}
  - {key: b, kind: check, title: "Schild lesbar?"}
""")


def _riso(text="20MΩ"):
    return ResultValue("riso", "RISO", Quantity.parse(text), Verdict.PASSED, ">1.00MΩ", "")


@pytest.fixture
def repeat(app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    first = app.service.create(press, "Erstprüfung", "Prüfer")
    app.service.add_measurement(first, "riso", [_riso()], datetime(2025, 5, 4, 9),
                                Verdict.PASSED, asset_id=cabinet)
    app.service.close(first)
    again = app.service.create(press, "Wiederholung", "Prüfer")
    app.service.make_repeat(again, first)
    return {"campaign": again, "press": press, "cabinet": cabinet}


def test_plans_join_the_points_and_stay_apart_from_them(app, repeat):
    campaign = repeat["campaign"]
    app.service.assign_plan(campaign, CHECKS)
    app.service.assign_plan(campaign, CHECKS)
    blocks = app.service.plan_blocks(campaign)
    assert [block.total for block in blocks] == [2, 2]
    assert len(app.service.points(campaign)) == 1
    record = app.service.campaign(campaign)
    assert record["plan_key"] == REPEAT
    assert record["plan_title"].endswith(" + Sichtprüfung + Sichtprüfung")


def test_removing_the_plans_keeps_the_points_and_their_key(app, repeat):
    campaign = repeat["campaign"]
    app.service.assign_plan(campaign, CHECKS)
    title = app.service.campaign(campaign)["plan_title"]
    app.service.remove_plan(campaign, app.service.plan_blocks(campaign)[0])
    record = app.service.campaign(campaign)
    assert record["plan_key"] == REPEAT and record["plan_title"] == title.split(" + ")[0]
    assert len(app.service.points(campaign)) == 1


def test_confirming_waits_for_the_points_and_the_plan_steps(app, repeat):
    campaign = repeat["campaign"]
    app.service.assign_plan(campaign, CHECKS)
    problems = app.service.blockers(campaign)
    assert any("Messpunkt" in text or "point" in text for text in problems)
    assert sum("Abdeckung" in text or "Schild" in text for text in problems) == 2
    app.service.add_measurement(campaign, "riso", [_riso()], datetime(2026, 5, 4, 9),
                                Verdict.PASSED, asset_id=repeat["cabinet"])
    app.service.rematch(campaign)
    for row in app.service.plan_step_rows(campaign):
        app.service.answer_step(row["id"], "yes")
    assert app.service.blockers(campaign) == []


def test_a_point_moves_across_a_plan_without_splitting_it(app, repeat):
    campaign = repeat["campaign"]
    app.service.assign_plan(campaign, CHECKS)
    point = app.service.points(campaign)[0][0]["id"]
    app.db.execute("UPDATE steps SET position=99 WHERE id=?", point)
    assert [block.total for block in app.service.plan_blocks(campaign)] == [2]


def test_the_report_shows_plan_steps_as_steps_beside_the_points(app, repeat):
    campaign = repeat["campaign"]
    app.service.assign_plan(campaign, CHECKS)
    context = build_context(app.service, campaign)
    titles = [step.title for step in context["steps"]]
    assert "Abdeckung vorhanden?" in titles and "Schild lesbar?" in titles


def test_a_test_plan_first_then_a_repeat_gives_the_repeat_key(app, repeat):
    again = app.service.create(repeat["press"], "Noch einmal", "Prüfer", CHECKS)
    app.service.make_repeat(again, app.service.last_closed(repeat["press"])["id"])
    assert app.service.campaign(again)["plan_key"] == REPEAT
    assert [block.title for block in app.service.plan_blocks(again)] == ["Sichtprüfung"]


def test_the_guide_lists_only_the_steps_of_the_plan_run(window, app, repeat):
    campaign = repeat["campaign"]
    app.service.assign_plan(campaign, CHECKS)
    app.service.assign_plan(campaign, parse_plan("""
key: more
title: Noch mehr
released: true
steps:
  - {key: c, kind: check, title: "Dritte Frage?"}
"""))
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    page.plan_list.list.setCurrentRow(1)
    page.plan_list.run_button.click()
    shown = [page.guided.steps.item(i).text() for i in range(page.guided.steps.count())]
    assert len(shown) == 1 and "Dritte Frage?" in shown[0]
    assert page.plan_section.isVisible() and page.assign_action.isEnabled()
