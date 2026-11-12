# EasyMeasurement - tests/test_plan_run_ui.py
# Test plans at the side of a campaign: run one in the middle, pause, end or remove it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from easymeasurement.campaign.plan import parse_plan
from easymeasurement.l10n import tr
from easymeasurement.ui import campaign_plans
from easymeasurement.ui.plan_list import progress_text
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


def test_a_plan_is_listed_and_the_middle_shows_the_measurements(page, app):
    block = app.service.plan_blocks(page.campaign_id)[0]
    assert page.plan_list.list.count() == 1
    assert page.plan_list.list.item(0).text() == f"{block.title}\n{progress_text(block)}"
    assert (block.done, block.total) == (0, 2)
    assert page.middle.currentWidget() is page.work


def test_running_takes_the_middle_and_pausing_gives_it_back(page, app):
    page.plan_list.run_button.click()
    assert page.middle.currentWidget() is page.plan_run
    assert not page.plan_list.run_button.isEnabled()
    page.guided.check_page.buttons["yes"].click()
    page.plan_run.pause_button.click()
    assert page.middle.currentWidget() is page.work
    assert page.plan_list.run_button.text() == tr("Continue")
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
    block = app.service.plan_blocks(page.campaign_id)[0]
    assert block.finished
    assert page.plan_list.list.item(0).text().endswith(progress_text(block))


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


def test_a_sequence_in_the_table_is_taken_over_as_a_plan(page, app, monkeypatch):
    from datetime import datetime

    from PySide6.QtWidgets import QMessageBox

    from easymeasurement.model import Quantity, ResultValue, Verdict
    from easymeasurement.ui.table_columns import GROUP
    run = app.service.add_run(page.campaign_id, "Sichtprüfung Halle", "Sichtprüfung",
                              datetime(2026, 5, 4, 9))
    values = [ResultValue("question", "Frage", Quantity(raw="Alles beschriftet?")),
              ResultValue("answer", "Antwort", Quantity(raw="yes"), Verdict.PASSED)]
    taken = app.service.add_measurement(page.campaign_id, "visual_inspection", values,
                                        datetime(2026, 5, 4, 9), Verdict.PASSED)
    app.service.join_run(taken, run, "Beschriftung")
    page.show_campaign(page.campaign_id)
    table = page.values.table
    row = next(r for r in range(table.rowCount()) if table.item(r, 0).data(GROUP) == run)
    told = []
    monkeypatch.setattr(QMessageBox, "information", lambda *args: told.append(args[2]))
    page.values.note_run(row)
    assert page.values.menu_run == run
    assert page.values.plan_action in page.values._menu_actions()
    page.values.plan_action.trigger()
    assert any(plan.title == "Sichtprüfung Halle" for plan in app.service.plans())
    assert "Sichtprüfung Halle" in told[0]
