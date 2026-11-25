# OkeyDocu - tests/test_unassigned_measurements.py
# l10n: de
# A measurement taken beside the plans and booked on an element is where it belongs.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.plan import parse_plan
from okeydocu.model import Quantity, ResultValue, Verdict

PLAN = parse_plan("""
key: sight
title: Besichtigung
released: true
steps:
  - {key: a, kind: check, title: "Typschild vorhanden?"}
""")


@pytest.fixture
def campaign(app, asset):
    """Its only question answered, so nothing but measurements can stand against ending."""
    campaign = app.service.create(asset, "Prüfung", "Anna Beispiel", PLAN)
    app.service.answer_step(app.service.steps(campaign)[0]["id"], "yes")
    return campaign


def measure(app, campaign, asset_id=None) -> int:
    value = ResultValue("rlo", "RLO", Quantity.parse("0,12 Ω"), Verdict.PASSED, "", "")
    return app.service.add_measurement(campaign, "rlo", [value], datetime(2026, 3, 9, 8, 30),
                                       Verdict.PASSED, asset_id=asset_id)


def summary(app, campaign):
    return next(row for row in app.service.summaries() if row.id == campaign)


def test_a_measurement_on_an_element_is_in_its_place(app, asset, campaign):
    measure(app, campaign, asset)
    assert app.service.unassigned_measurements(campaign) == []
    assert app.service.blockers(campaign) == []
    assert summary(app, campaign).loose == 0


def test_a_measurement_with_neither_step_nor_element_belongs_nowhere(app, campaign):
    measure(app, campaign)
    assert len(app.service.unassigned_measurements(campaign)) == 1
    assert app.service.blockers(campaign) == [
        "1 Messung weder einem Messschritt noch einem Element zugeordnet"]
    assert summary(app, campaign).loose == 1
