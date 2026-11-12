# EasyMeasurement - tests/test_plan_blocks.py
# The plans of a campaign one by one: progress, pausing, ending and removing one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from easymeasurement.campaign.plan import parse_plan
from easymeasurement.model import Quantity, ResultValue, Verdict

SIGHT = """
key: sight
released: true
title: Sichtprüfung
steps:
  - {key: b, kind: check, title: "Abdeckung vorhanden?"}
  - {key: d, function: rlo}
"""
SECOND = """
key: second
released: true
title: Isolation
steps:
  - {key: r, function: riso}
"""


@pytest.fixture
def campaign(service, asset_id):
    campaign = service.create(asset_id, "T", "Anna", parse_plan(SIGHT))
    service.assign_plan(campaign, parse_plan(SECOND))
    service.assign_plan(campaign, parse_plan(SIGHT))
    return campaign


def test_each_assignment_is_a_plan_of_its_own(service, campaign):
    blocks = service.plan_blocks(campaign)
    assert [(b.title, b.total, b.done) for b in blocks] == [
        ("Sichtprüfung", 2, 0), ("Isolation", 1, 0), ("Sichtprüfung", 2, 0)]
    first = blocks[0]
    service.answer_step(first.step_ids[0], "yes")
    assert service.plan_blocks(campaign)[0].done == 1
    assert service.first_open_step(service.plan_blocks(campaign)[0]) == first.step_ids[1]


def test_pausing_stops_the_step_being_measured(service, campaign):
    step = service.plan_blocks(campaign)[1].step_ids[0]
    service.confirm_setup(step)
    service.pause_plans(campaign)
    assert service.db.one("SELECT status FROM steps WHERE id=?", step)["status"] == "pending"


def test_ending_skips_what_is_open_with_one_reason(service, campaign):
    block = service.plan_blocks(campaign)[0]
    service.answer_step(block.step_ids[0], "yes")
    service.end_plan(block, "Anlage nicht zugänglich")
    states = [tuple(service.db.one("SELECT status, note FROM steps WHERE id=?", s))
              for s in block.step_ids]
    assert states == [("done", ""), ("skipped", "Anlage nicht zugänglich")]
    assert service.plan_blocks(campaign)[0].finished


def test_removing_a_plan_takes_its_steps_with_everything_booked_on_them(service, campaign):
    blocks = service.plan_blocks(campaign)
    service.answer_step(blocks[2].step_ids[0], "no", "fehlt")
    value = ResultValue("rlo", "RLO", Quantity.parse("0.2Ω"), Verdict.PASSED, "", "")
    service.add_measurement(campaign, "rlo", [value], datetime(2026, 5, 4, 9), Verdict.PASSED,
                            step_id=blocks[2].step_ids[1])
    free = service.add_measurement(campaign, "rlo", [value], datetime(2026, 5, 4, 9),
                                   Verdict.PASSED)
    assert service.booked_on(blocks[2]) == 2
    service.remove_plan(campaign, blocks[2])
    assert [b.title for b in service.plan_blocks(campaign)] == ["Sichtprüfung", "Isolation"]
    assert service.campaign(campaign)["plan_title"] == "Sichtprüfung + Isolation"
    assert [m["id"] for m in service.measurements(campaign)] == [free]


def test_without_any_plan_left_the_campaign_has_none(service, campaign):
    for block in service.plan_blocks(campaign):
        service.remove_plan(campaign, block)
    row = service.campaign(campaign)
    assert (row["plan_key"], row["plan_title"]) == ("", "")
