# OkeyDocu - tests/test_report_plans_first.py
# l10n: de
# A report ordered by measured quantity states the test plans first, then the readings.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.plan import parse_plan
from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.reporting.context import build_context
from okeydocu.reporting.language import speaking
from okeydocu.reporting.nodes import Fields, Heading, Paragraph, plain
from okeydocu.reporting.template import resolve

SIGHT = parse_plan("""
key: sight
title: Besichtigung
released: true
steps:
  - {key: a, kind: check, title: "Typschild vorhanden?"}
  - {key: b, kind: check, title: "Drehfeld gekennzeichnet?"}
  - {key: c, kind: check, title: "Schaltplan vorhanden?"}
""")
TEST = parse_plan("""
key: test
title: Messungen
released: true
steps:
  - {key: a, function: rlo, title: "Schutzleiter Motor"}
  - {key: b, function: riso, title: "Isolation Motor"}
""")
EARLY = datetime(2026, 3, 9, 8, 0)


@pytest.fixture
def campaign(app, asset):
    """A reading without a plan taken first, then two plans: one asks, one measures."""
    service = app.service
    campaign = service.create(asset, "Prüfung", "Anna Beispiel", SIGHT)
    volts = ResultValue("u", "U", Quantity.parse("230V"), Verdict.PASSED)
    service.add_measurement(campaign, "u", [volts], EARLY, Verdict.PASSED, asset_id=asset)
    service.assign_plan(campaign, TEST)
    first, second, third, low, high = service.steps(campaign)
    service.answer_step(first["id"], "yes")
    service.skip_step(second["id"], "kein Drehstrom")
    ohms = ResultValue("rlo", "RLO", Quantity.parse("0.10Ω"), Verdict.PASSED, "", "<1.00Ω")
    service.add_measurement(campaign, "rlo", [ohms], verdict=Verdict.PASSED, step_id=low["id"],
                            asset_id=asset)
    service.finish_step(low["id"])
    return campaign


def nodes_of(app, campaign, order):
    with speaking("de"):
        block = {"type": "structure", "order": order}
        return resolve({"blocks": [block]}, build_context(app.service, campaign))


def headings(nodes):
    return [(plain(node.text), node.level) for node in nodes if isinstance(node, Heading)]


@pytest.mark.parametrize("order", ("function_time", "function"))
def test_the_plans_stand_before_the_measured_quantities(app, campaign, order):
    found = [text for text, level in headings(nodes_of(app, campaign, order)) if level == 2]
    assert found == ["Besichtigung", "Messungen", "U – Spannung",
                     "RLO – Schutzleiterwiderstand"]


def test_a_plan_says_what_it_left_out_and_what_it_lacks(app, campaign):
    nodes = nodes_of(app, campaign, "function_time")
    assert headings(nodes)[:5] == [
        ("Besichtigung", 2), ("Ausgelassene Prüffragen mit Begründung", 3),
        ("Nicht gemessen", 3), ("Messungen", 2), ("Nicht gemessen", 3)]
    lists = [node.rows for node in nodes if isinstance(node, Fields)]
    assert [("Drehfeld gekennzeichnet?", "kein Drehstrom")] in lists
    assert [("Schaltplan vorhanden?", "ohne Angabe eines Grundes")] in lists
    assert [("Isolation Motor", "ohne Angabe eines Grundes")] in lists
    said = [node.text for node in nodes if isinstance(node, Paragraph)]
    assert "Der Messwert von 1 Messschritt steht unten bei seiner Messgröße." in said


def test_ordered_by_place_the_plans_stay_with_the_elements(app, campaign):
    found = [text for text, level in headings(nodes_of(app, campaign, "place")) if level == 2]
    assert found[0] != "Besichtigung"
    assert found[-2:] == ["Ausgelassene Prüffragen mit Begründung", "Nicht gemessen"]
