# OkeyDocu - tests/test_line_conductors.py
# Line conductors and N at a test point, and readings against missing ones left out.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.line_conductors import ConductorBook, Conductors, failed_counts
from okeydocu.devices import LiveReading
from okeydocu.model import CONDUCTOR, MeterMeasurement, Parameter, Quantity, ResultValue, \
    Verdict
from okeydocu.reporting.context import build_context


@pytest.mark.parametrize("conductors, path, lacking", [
    (Conductors(1, True), "L1-PE", False), (Conductors(1, True), "L2-PE", True),
    (Conductors(1, True), "L1-L3", True), (Conductors(3, True), "L3-N", False),
    (Conductors(3, False), "L3-N", True), (Conductors(3, False), "L+N-PE", True),
    (Conductors(None, None), "L2-N", False), (Conductors(1, None), "L-N", False)])
def test_a_path_needs_every_conductor_it_names(conductors, path, lacking):
    assert conductors.lacks(path) is lacking


@pytest.fixture
def plant(db):
    customer = db.add_customer("Muster AG")
    machine = db.add_asset(customer, "machine", "Presse")
    db.set_asset_features(machine, {"line_conductors": "3", "n_conductor": "without N"})
    board = db.add_asset(customer, "distribution_board", "Schrank", machine)
    socket = db.add_asset(customer, "circuit", "Steckdose", board)
    db.set_asset_features(socket, {"line_conductors": "1", "n_conductor": "ohne N"})
    return {"machine": machine, "board": board, "socket": socket}


def test_what_an_element_leaves_open_comes_from_above(db, plant):
    book = ConductorBook(db)
    assert book.at(plant["board"]) == Conductors(3, False)
    assert book.at(plant["socket"]) == Conductors(1, False)
    db.set_asset_features(plant["board"], {"n_conductor": "with N"})
    assert ConductorBook(db).at(plant["board"]) == Conductors(3, True)


def measured(path: str, verdict: Verdict, minute: int) -> LiveReading:
    taken = datetime(2026, 11, 14, 9, minute)
    return LiveReading(MeterMeasurement(
        uid=f"u-{minute}", function="u", taken_at=taken, verdict=verdict,
        parameters=(Parameter(CONDUCTOR, path),),
        results=(ResultValue("u", "U", Quantity.parse("0V" if verdict is Verdict.FAILED
                                                      else "231V")),)), taken)


@pytest.fixture
def campaign(service, plant):
    started = service.create(plant["machine"], "Prüfung", "Tester")
    for minute, (path, verdict) in enumerate((("L1-PE", Verdict.PASSED),
                                              ("L2-PE", Verdict.FAILED),
                                              ("N-PE", Verdict.FAILED))):
        service.receive(started, measured(path, verdict, minute), plant["socket"])
    return started


def test_readings_against_missing_conductors_are_left_out_of_verdict_and_report(
        service, campaign):
    rows = service.measurements(campaign)
    assert len(rows) == 3
    assert len(ConductorBook(service.db).omitted_ids(rows)) == 2
    assert failed_counts(service.db) == {}
    reported = [m for step in build_context(service, campaign)["steps"]
                for m in step.measurements]
    assert [m.data.parameters[0].value for m in reported] == ["L1-PE"]


def test_the_mark_follows_the_element(service, campaign, plant):
    service.db.set_asset_features(plant["socket"], {"line_conductors": "3",
                                                    "n_conductor": "with N"})
    assert failed_counts(service.db) == {campaign: 2}
