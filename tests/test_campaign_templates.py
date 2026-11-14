# OkeyDocu - tests/test_campaign_templates.py
# Campaign templates: made from an inspection, taken on the same or another installation,
# edited on the way and learning from what a campaign did differently.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.template_learning import DROPPED, HINT, NEW, ORDER
from okeydocu.campaign.template_use import renamed
from okeydocu.campaign.templates import SERIES
from okeydocu.model import Quantity, ResultValue, Verdict


@pytest.fixture
def press(db):
    customer = db.add_customer("Muster AG")
    machine = db.add_asset(customer, "machine", "Presse 7")
    cabinet = db.add_asset(customer, "distribution_board", "Schrank", machine, identifier="=K1")
    motor = db.add_asset(customer, "electric_engine", "Motor", cabinet, identifier="=M1")
    db.set_asset_features(motor, {"rated_power": "4"})
    return {"customer": customer, "machine": machine, "cabinet": cabinet, "motor": motor}


def measure(service, campaign, asset_id, minute, function="riso", hint=""):
    value = ResultValue(function, function.upper(), Quantity.parse("200MΩ"), Verdict.PASSED,
                        ">1MΩ", "")
    measurement = service.add_measurement(campaign, function, [value],
                                          datetime(2026, 11, 14, 9, minute), Verdict.PASSED,
                                          asset_id=asset_id)
    if hint:
        service.db.execute("UPDATE measurements SET hint=? WHERE id=?", hint, measurement)
    return measurement


@pytest.fixture
def template(service, press):
    first = service.create(press["machine"], "Erstprüfung", "Prüfer")
    measure(service, first, press["motor"], 1)
    measure(service, first, press["cabinet"], 2, "rlo")
    service.close(first)
    return service.template_from(first, "Presse, elektrisch")


def test_a_template_keeps_tree_and_points_in_their_order_but_no_value(service, press, template):
    kept = service.template(template)
    assert [node["name"] for node in kept.nodes] == ["Presse 7", "Schrank", "Motor"]
    assert kept.nodes[2]["features"] == {"rated_power": "4"}
    assert [point["function"] for point in kept.points] == ["riso", "rlo"]
    assert all("200" not in str(point) for point in kept.points)
    assert template not in [row["key"] for row in service.db.plans()]


def test_on_the_same_installation_the_points_lie_at_its_elements(service, press, template):
    campaign = service.create(press["machine"], "Wiederholung", "Prüfer")
    service.use_template(campaign, template)
    points = service.points(campaign)
    assert [step.asset_id for _, step in points] == [press["motor"], press["cabinet"]]
    measure(service, campaign, press["motor"], 5)
    assert [row["status"] for row, _ in service.points(campaign)] == ["done", "pending"]
    assert service.next_point(campaign, points[0][0]["id"]) == press["cabinet"]


def test_on_another_installation_the_tree_is_made_anew_with_its_names(service, press, template):
    other = service.db.add_asset(press["customer"], "machine", "Presse 8")
    assert service.copy_needed(template, other)
    nodes = renamed(service.template(template))
    assert [(node["name"], node["depth"]) for node in nodes] == [("Schrank", 1), ("Motor", 2)]
    campaign = service.create(other, "Serienprüfung", "Prüfer")
    service.use_template(campaign, template, {nodes[0]["key"]: ("Schrank", "=K2")})
    motor = service.points(campaign)[0][1].asset_id
    row = service.db.asset(motor)
    assert row["name"] == "Motor" and service.db.asset(row["parent_id"])["identifier"] == "=K2"
    assert service.db.asset_features(motor) == {"rated_power": "4"}
    assert motor in service.subtree(other)


def test_an_open_campaign_adds_moves_and_removes_points(service, press, template):
    campaign = service.create(press["machine"], "Wiederholung", "Prüfer")
    service.use_template(campaign, template)
    first, second = (row["id"] for row, _ in service.points(campaign))
    service.move_point(second, -1)
    assert [row["id"] for row, _ in service.points(campaign)] == [second, first]
    service.remove_point(second)
    loose = measure(service, campaign, press["machine"], 7, "u")
    added = service.add_point_from(loose)
    assert [row["id"] for row, _ in service.points(campaign)] == [first, added]
    assert service.point_measurement(added)["id"] == loose


def test_an_open_template_asks_no_reasons_a_series_does(service, press, template):
    campaign = service.create(press["machine"], "Wiederholung", "Prüfer")
    service.use_template(campaign, template)
    assert len(service.blockers(campaign)) == 1  # the points still open
    kept = service.template(template)
    kept.mode = SERIES
    service.save_template(kept)
    assert service.template_mode(service.campaign(campaign)["plan_key"]) == SERIES


def test_what_a_campaign_did_differently_can_be_learned(service, press, template):
    campaign = service.create(press["machine"], "Wiederholung", "Prüfer")
    service.use_template(campaign, template)
    measure(service, campaign, press["cabinet"], 1, "rlo")
    measure(service, campaign, press["motor"], 2, hint="Klemmkasten erst öffnen")
    added = service.add_point_from(measure(service, campaign, press["machine"], 3, "u"))
    changes = service.template_changes(campaign)
    assert {change.kind for change in changes} == {NEW, HINT, ORDER}
    assert next(c for c in changes if c.kind == NEW).step_id == added
    service.learn(campaign, changes)
    kept = service.template(template)
    assert [point["function"] for point in kept.points] == ["rlo", "riso", "u"]
    assert kept.points[1]["hint"] == "Klemmkasten erst öffnen"
    assert len(kept.learned) == 2


def test_a_point_left_out_can_leave_the_template(service, press, template):
    campaign = service.create(press["machine"], "Wiederholung", "Prüfer")
    service.use_template(campaign, template)
    service.remove_point(service.points(campaign)[1][0]["id"])
    changes = service.template_changes(campaign)
    assert [change.kind for change in changes] == [DROPPED]
    service.learn(campaign, changes)
    assert [point["function"] for point in service.template(template).points] == ["riso"]
