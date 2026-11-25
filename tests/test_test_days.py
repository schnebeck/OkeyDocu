# OkeyDocu - tests/test_test_days.py
# A test is dated by its measurements, its report by the day it was signed.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from datetime import date, datetime

import pytest

from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.reporting.context import build_context
from okeydocu.reporting.context_texts import signing_day
from okeydocu.reporting.language import speaking
from okeydocu.ui.campaign_items import campaign_lines

CREATED = "2026-03-02T14:00:00"


@pytest.fixture
def campaign(app, asset):
    """Created a week before anything is measured."""
    campaign = app.service.create(asset, "Inspection", "Anna Example")
    app.db.execute("UPDATE campaigns SET started_at=? WHERE id=?", CREATED, campaign)
    return campaign


def measure(app, campaign, moment: datetime) -> None:
    value = ResultValue("rlo", "RLO", Quantity.parse("0,12 Ω"), Verdict.PASSED, "", "")
    app.service.add_measurement(campaign, "rlo", [value], moment, Verdict.PASSED)


def told(app, campaign) -> dict:
    with speaking("de"):
        return build_context(app.service, campaign)["campaign"]


def test_until_something_is_measured_the_creation_stands_in(app, campaign):
    assert app.service.test_days(campaign) == (date(2026, 3, 2), date(2026, 3, 2))
    assert app.service.campaign(campaign)["tested_at"] == CREATED
    assert told(app, campaign)["date"] == "02.03.2026"


def test_the_report_names_the_day_measured_on(app, campaign):
    measure(app, campaign, datetime(2026, 3, 9, 8, 30))
    measure(app, campaign, datetime(2026, 3, 9, 15, 0))
    assert told(app, campaign)["date"] == "09.03.2026"
    assert told(app, campaign)["started"] == "09.03.2026 08:30"


def test_a_test_over_several_days_names_the_first_and_the_last(app, campaign):
    measure(app, campaign, datetime(2026, 3, 11, 9, 0))
    measure(app, campaign, datetime(2026, 3, 9, 8, 30))
    assert app.service.test_days(campaign) == (date(2026, 3, 9), date(2026, 3, 11))
    assert told(app, campaign)["date"] == "09.03.2026 – 11.03.2026"


def test_the_list_of_campaigns_tells_when_the_test_began(app, campaign):
    measure(app, campaign, datetime(2026, 3, 9, 8, 30))
    row = next(row for row in app.service.campaigns() if row["id"] == campaign)
    assert "09.03.2026 08:30" in campaign_lines(row, 1)


def test_the_test_begun_last_is_listed_first(app, asset, campaign):
    later = app.service.create(asset, "Second", "Anna Example")
    app.db.execute("UPDATE campaigns SET started_at='2026-03-05T10:00:00' WHERE id=?", later)
    assert [row["id"] for row in app.service.campaigns()] == [later, campaign]
    measure(app, campaign, datetime(2026, 3, 9, 8, 30))
    assert [row["id"] for row in app.service.campaigns()] == [campaign, later]


def test_calibration_is_judged_on_the_last_day_measured(app, campaign):
    device = json.dumps({"manufacturer": "Example", "model": "Tester 1", "serial_no": "A1",
                         "recalibration_due": "2026-03-05"})
    app.db.execute("UPDATE campaigns SET device_json=? WHERE id=?", device, campaign)
    with speaking("de"):
        assert not build_context(app.service, campaign)["device"]["overdue"]
        measure(app, campaign, datetime(2026, 3, 9, 8, 30))
        assert build_context(app.service, campaign)["device"]["overdue"]


def test_the_report_is_dated_by_the_day_it_was_signed():
    assert signing_day({"closed_at": "2026-03-12T16:00:00"}) == date(2026, 3, 12)
    assert signing_day({"closed_at": None}) == date.today()


def test_an_ended_campaign_keeps_both_days_apart(app, campaign):
    measure(app, campaign, datetime(2026, 3, 9, 8, 30))
    app.service.close(campaign)
    closed = datetime.fromisoformat(app.service.campaign(campaign)["closed_at"])
    with speaking("de"):
        report = build_context(app.service, campaign)
    assert report["report"]["date"] == closed.strftime("%d.%m.%Y")
    assert report["campaign"]["date"] == "09.03.2026"
