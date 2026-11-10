# EasyMeasurement - tests/test_structure.py
# Rebuilding the structure of an installation and booking measurements onto its elements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from easymeasurement.campaign.service import StructureError
from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.store import CampaignClosed


@pytest.fixture
def tree(app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schaltschrank", parent_id=press)
    point = app.db.add_asset(customer, "measuring_point", "X1", parent_id=cabinet)
    spare = app.db.add_asset(customer, "measuring_point", "Leer", parent_id=press)
    return {"customer": customer, "press": press, "cabinet": cabinet, "point": point,
            "spare": spare}


def _measure(app, campaign, asset_id=None, location=""):
    value = ResultValue("riso", "RISO", Quantity.parse("2MΩ"), Verdict.PASSED, ">1MΩ", "")
    return app.service.add_measurement(campaign, "riso", [value], datetime(2026, 5, 4, 9),
                                       Verdict.PASSED, location=location, asset_id=asset_id)


def test_a_measurement_moves_and_reads_its_new_place(app, tree):
    campaign = app.service.create(tree["press"], "Prüfung", "Prüfer")
    cable = app.service.add_element(tree["cabinet"], "cable", "Anschlusskabel")
    measurement = _measure(app, campaign, tree["cabinet"])
    app.service.move_measurements([measurement], cable)
    row = app.db.one("SELECT * FROM measurements WHERE id=?", measurement)
    assert row["asset_id"] == cable
    assert row["location"] == "Presse / Schaltschrank / Anschlusskabel"
    assert app.service.measurement_changes(measurement) == []  # the place is no reading


def test_a_sealed_measurement_stays_where_it_is(app, tree):
    campaign = app.service.create(tree["press"], "Prüfung", "Prüfer")
    measurement = _measure(app, campaign, tree["cabinet"])
    app.service.close(campaign)
    with pytest.raises(CampaignClosed):
        app.service.move_measurements([measurement], tree["point"])


def test_renaming_and_moving_follow_into_open_measurements(app, tree):
    campaign = app.service.create(tree["press"], "Prüfung", "Prüfer")
    measurement = _measure(app, campaign, tree["point"])
    app.service.rename_element(tree["point"], "X2")
    app.service.move_element(tree["point"], tree["press"])
    row = app.db.one("SELECT location FROM measurements WHERE id=?", measurement)
    assert row["location"] == "Presse / X2"


def test_an_element_cannot_go_below_itself(app, tree):
    with pytest.raises(StructureError):
        app.service.move_element(tree["press"], tree["point"])


def test_machines_are_grouped_into_an_installation(app, tree):
    other = app.db.add_asset(tree["customer"], "machine", "Säge")
    hall = app.service.group_elements([tree["press"], other], "installation", "Halle 3")
    assert {a["parent_id"] for a in map(app.db.asset, (tree["press"], other))} == {hall}
    assert app.db.asset(hall)["parent_id"] is None


def test_deleting_moves_open_measurements_up(app, tree):
    campaign = app.service.create(tree["press"], "Prüfung", "Prüfer")
    measurement = _measure(app, campaign, tree["point"])
    app.service.delete_element(tree["cabinet"])
    assert app.db.asset(tree["point"]) is None
    row = app.db.one("SELECT * FROM measurements WHERE id=?", measurement)
    assert (row["asset_id"], row["location"]) == (tree["press"], "Presse")


def test_what_a_sealed_record_or_a_campaign_needs_stays(app, tree):
    campaign = app.service.create(tree["press"], "Prüfung", "Prüfer")
    _measure(app, campaign, tree["point"])
    app.service.close(campaign)
    assert "Abgeschlossene" in app.service.deletion_blocker(tree["cabinet"])
    assert "Kampagne" in app.service.deletion_blocker(tree["press"])
    with pytest.raises(StructureError):
        app.service.delete_element(tree["point"])


def test_empty_branches_are_found_from_the_top(app, tree):
    campaign = app.service.create(tree["press"], "Prüfung", "Prüfer")
    _measure(app, campaign, tree["point"])
    deep = app.service.add_element(tree["spare"], "measuring_point", "Noch leerer")
    assert app.service.empty_elements(tree["press"]) == [tree["spare"]]
    assert deep not in app.service.empty_elements(tree["press"])


def test_a_device_path_finds_or_creates_its_element(app, tree):
    found = app.service.place_for_path(tree["press"], ("Muster AG", "Presse", "Schaltschrank", "X1"))
    assert found == tree["point"]
    new = app.service.place_for_path(tree["press"], ("Schaltschrank", "X9"))
    assert app.db.asset(new)["parent_id"] == tree["cabinet"]
    assert app.db.asset(new)["kind"] == "measuring_point"


def test_counts_tell_this_campaign_from_the_last(app, tree):
    first = app.service.create(tree["press"], "Erst", "Prüfer")
    _measure(app, first, tree["point"])
    _measure(app, first, tree["point"])
    app.service.close(first)
    second = app.service.create(tree["press"], "Wieder", "Prüfer")
    _measure(app, second, tree["cabinet"])
    assert app.service.place_counts(second) == {tree["cabinet"]: 1}
    assert app.service.previous_counts(second) == {tree["point"]: 2}


# Kinds -----------------------------------------------------------------------


def test_a_fresh_database_knows_the_shipped_kinds(app):
    labels = app.db.kind_labels()
    assert labels["machine"] == "Maschine" and labels["extinguisher"] == "Feuerlöscher"
    assert len(labels) >= 28
    machine = app.db.kind("machine")
    assert machine.izytron_type == 231 and machine.device_type == "MACHINE"
    assert any(f.label == "Nennstrom" and f.unit == "A" for f in machine.features)


def test_a_kind_in_use_gives_its_elements_a_new_one(app, tree):
    assert app.db.kind_usage("distribution_board") == 1
    app.db.delete_kind("distribution_board", "cable")
    assert app.db.asset(tree["cabinet"])["kind"] == "cable"
    assert app.db.kind("distribution_board") is None


def test_empty_features_are_not_kept(app, tree):
    app.db.set_asset_features(tree["press"], {"nennstrom": " 16 ", "baujahr": "  "})
    assert app.db.asset_features(tree["press"]) == {"nennstrom": "16"}


# Due again -------------------------------------------------------------------


def _closed(app, asset, title, closed_at, failed=False):
    campaign = app.service.create(asset, title, "Prüfer")
    if failed:
        value = ResultValue("riso", "RISO", Quantity.parse("0.2MΩ"), Verdict.FAILED, ">1MΩ", "")
        app.service.add_measurement(campaign, "riso", [value], datetime(2025, 1, 2), Verdict.FAILED)
    app.service.close(campaign)
    app.db.connection.execute("DROP TRIGGER IF EXISTS campaign_no_reopen")
    app.db.execute("UPDATE campaigns SET closed_at=? WHERE id=?", closed_at, campaign)
    return campaign


def test_months_are_added_to_the_last_day_that_exists():
    from datetime import date
    from easymeasurement.campaign.due import add_months
    assert add_months(date(2025, 1, 31), 1) == date(2025, 2, 28)
    assert add_months(date(2025, 11, 15), 14) == date(2027, 1, 15)


def test_an_inspection_is_due_once_its_interval_runs_out(app, tree):
    from datetime import date
    _closed(app, tree["press"], "Erst", "2025-01-10T09:00:00")  # machines: every 12 months
    due, = app.service.due_inspections(today=date(2026, 1, 1))
    assert (due.asset, due.due) == ("Presse", date(2026, 1, 10))
    assert app.service.due_inspections(today=date(2025, 6, 1)) == []


def test_an_element_may_have_its_own_interval_or_none(app, tree):
    from datetime import date
    _closed(app, tree["press"], "Erst", "2025-01-10T09:00:00")
    app.db.set_asset_interval(tree["press"], 0)
    assert app.service.due_inspections(today=date(2027, 1, 1)) == []


def test_an_open_campaign_on_the_element_takes_care_of_it(app, tree):
    from datetime import date
    _closed(app, tree["press"], "Erst", "2025-01-10T09:00:00")
    app.service.create(tree["press"], "Wieder", "Prüfer")
    assert app.service.due_inspections(today=date(2026, 6, 1)) == []


def test_defects_wait_for_a_follow_up(app, tree):
    first = _closed(app, tree["press"], "Erst", "2025-01-10T09:00:00", failed=True)
    follow, = app.service.open_follow_ups()
    assert (follow.campaign_id, follow.failed) == (first, 1)
    again = app.service.create(tree["press"], "Nachprüfung", "Prüfer")
    app.service.mark_follow_up(again, first)
    assert app.service.open_follow_ups() == []
