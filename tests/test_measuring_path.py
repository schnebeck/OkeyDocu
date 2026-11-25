# OkeyDocu - tests/test_measuring_path.py
# Setting right between which conductors a measurement was taken.
# l10n: de
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument names the pair its measuring path stood on, not the pair the probes were
on. The pair can be set right afterwards; what was read stays untouched."""

import json
from datetime import datetime

import pytest

from okeydocu.devices.base import LiveReading
from okeydocu.model import CONDUCTOR, MeterMeasurement, Parameter, Quantity, ResultValue, Verdict
from okeydocu.store import CampaignClosed


def taken(minute: int, parameters=(Parameter(CONDUCTOR, "L1-PE"),)) -> LiveReading:
    moment = datetime(2026, 11, 14, 9, minute)
    return LiveReading(MeterMeasurement(
        uid=f"u-{minute}", function="riso", taken_at=moment, verdict=Verdict.PASSED,
        parameters=parameters,
        results=(ResultValue("riso", "RISO", Quantity.parse("550MΩ")),)), moment)


@pytest.fixture
def campaign(app):
    machine = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    started = app.service.create(machine, "Prüfung", "Prüfer")
    for minute in range(3):
        app.service.receive(started, taken(minute), machine)
    return started


def first(app, campaign):
    return app.service.measurements(campaign)[0]


def test_the_pair_is_set_right_and_the_reading_stays(app, campaign):
    row = first(app, campaign)
    before = [dict(value) for value in app.service.values(row["id"])]
    assert app.service.set_conductor(row["id"], "L2-PE")
    after = app.service.measurements(campaign)[0]
    assert json.loads(after["parameters_json"]) == [{"key": CONDUCTOR, "value": "L2-PE"}]
    assert [dict(value) for value in app.service.values(row["id"])] == before
    assert after["verdict"] == row["verdict"] and after["local_time"] == row["local_time"]


def test_the_change_is_logged_with_the_old_and_the_new_pair(app, campaign):
    row = first(app, campaign)
    app.service.set_conductor(row["id"], "N-PE")
    change = app.service.measurement_changes(row["id"])[-1]
    assert (change["action"], change["field"]) == ("edit", CONDUCTOR)
    assert (change["old_value"], change["new_value"]) == ("L1-PE", "N-PE")


def test_the_same_pair_again_changes_nothing(app, campaign):
    row = first(app, campaign)
    assert not app.service.set_conductor(row["id"], "L1-PE")
    assert not app.service.measurement_changes(row["id"])


def test_an_ended_campaign_keeps_its_pairs(app, campaign):
    row = first(app, campaign)
    app.service.close(campaign)
    with pytest.raises(CampaignClosed):
        app.service.set_conductor(row["id"], "L3-PE")


def test_the_row_menu_sets_the_pair_of_the_chosen_rows(window, app, campaign):
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    values = page.values
    values.table.selectRow(1)
    assert values.path_action in values._menu_actions()
    values._set_path("L3-PE")
    texts = [values.table.item(row, column).text() for row in range(values.table.rowCount())
             for column in range(values.table.columnCount())]
    assert sum("L3-PE" in text for text in texts) == 1
    assert sum("L1-PE" in text for text in texts) == 2


def test_a_row_without_a_pair_offers_no_change(window, app, campaign):
    app.service.add_measurement(campaign, "u", [ResultValue("u", "U", Quantity.parse("230V"))],
                                datetime(2026, 11, 14, 10))
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    values = page.values
    row = next(r for r in range(values.table.rowCount())
               if not any("-PE" in values.table.item(r, c).text()
                          for c in range(values.table.columnCount())))
    values.table.selectRow(row)
    assert values.path_action not in values._menu_actions()
