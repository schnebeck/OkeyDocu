# OkeyDocu - tests/test_rcd_in_front.py
# l10n: de
# An RCD of the building installation: stated at the installation, measured at its supply.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.measuring_place import in_front_place, measuring_place
from okeydocu.campaign.setting_check import Mismatch, NoRcd, SettingCheck
from okeydocu.devices import LiveReading
from okeydocu.devices.guide import IN_FRONT, RCD_PLACE, SELECT
from okeydocu.devices.profitest_prime.guides import guide_for
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.l10n import speaking
from okeydocu.model import MeterMeasurement, Parameter, Verdict
from okeydocu.ui.measuring_window import MeasuringWindow

IN_FRONT_OF_PRESS = {"upstream_rcd_type": "A", "upstream_residual_current": "30",
                     "upstream_rated_current": "40"}


@pytest.fixture
def press(app):
    """A machine without an RCD of its own, a circuit in it, and a campaign on it."""
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse", identifier="=M10")
    circuit = app.db.add_asset(customer, "circuit", "Steuerung", machine)
    campaign = app.service.create(machine, "Prüfung", "Tester")
    return {"machine": machine, "circuit": circuit, "campaign": campaign,
            "customer": customer}


def place_of(app, press, asset, function="rcd_time"):
    return measuring_place(app.service, guide_for(function), asset, press["machine"])


def test_without_an_rcd_anywhere_the_measurement_has_no_place(app, press):
    assert place_of(app, press, press["circuit"]).asset_id is None


def test_the_rcd_in_front_makes_the_chosen_element_the_place(app, press):
    app.db.set_asset_features(press["machine"], IN_FRONT_OF_PRESS)
    place = place_of(app, press, press["circuit"])
    assert (place.asset_id, place.holder_id) == (press["circuit"], press["machine"])
    assert place.in_front and place.stated(RCD_PLACE) == IN_FRONT
    assert place.stated("rcd_type") == "A"
    assert place.stated("rated_residual_current") == "30 mA"
    assert place.lines() == ["30 mA · A", "40 A"]


def test_an_rcd_of_the_installation_comes_before_the_one_in_front(app, press):
    app.db.set_asset_features(press["machine"], IN_FRONT_OF_PRESS)
    own = app.db.add_asset(press["customer"], "rcd", "FI", press["machine"])
    socket = app.db.add_asset(press["customer"], "circuit", "Steckdose", own)
    place = place_of(app, press, socket)
    assert place.asset_id == own and not place.in_front


def test_a_measurement_that_needs_no_rcd_is_taken_as_ever(app, press):
    app.db.set_asset_features(press["machine"], IN_FRONT_OF_PRESS)
    place = place_of(app, press, press["circuit"], "rlo")
    assert place.asset_id == press["circuit"] and not place.in_front
    assert place.stated("rcd_type") == ""


def test_an_installation_that_cannot_state_one_has_none_in_front(app, press):
    hall = app.db.add_asset(press["customer"], "installation", "Halle")
    assert in_front_place(app.service, hall, hall) is None


@pytest.mark.parametrize("function, terminals", [
    ("rcd_time", ["pe", "in_l1", "in_n"]), ("zloop_dc", ["pe", "in_l1", "in_n"]),
    ("zloop_rlo", ["pe", "in_l1", "in_n"]), ("zloop_half", ["pe", "in_l1"])])
def test_with_the_rcd_in_front_the_probes_go_to_the_main_switch(function, terminals):
    guide = guide_for(function)
    taken = guide.suited(lambda key: IN_FRONT if key == RCD_PLACE else "")
    assert taken.test_object == "main_switch"
    assert [lead.terminal for lead in taken.leads] == terminals
    assert guide.suited(lambda key: "").test_object == "rcd"


def test_settings_are_held_against_the_rcd_in_front(app, press):
    app.db.set_asset_features(press["machine"], IN_FRONT_OF_PRESS)
    check = SettingCheck(app.db)
    assert check.expected(press["circuit"]) == [
        ("rcd_type", "A"), ("rated_residual_current", "30 mA"), ("rated_current", "40 A")]
    with speaking("de"):
        found = check.findings("rcd_time", [("rcd_type", "B"), ("rated_current", "40A")],
                               press["circuit"])
        assert found == [Mismatch("rcd_type", "B", "A", "dem vorgeschalteten RCD von =M10")]


def test_an_rcd_test_with_no_rcd_at_all_stays_a_finding(app, press):
    assert SettingCheck(app.db).findings("rcd_time", [], press["circuit"]) == [NoRcd()]


def opened(qtbot, app, press, asset, function="rcd_time"):
    with speaking("de"):
        shown = MeasuringWindow(app, press["campaign"], DRIVER_KEY, function, asset)
    qtbot.addWidget(shown)
    shown.resize(1440, 1020)
    shown.show()
    return shown


def test_the_station_asks_where_the_rcd_stands_and_states_the_one_in_front(qtbot, app, press):
    shown = opened(qtbot, app, press, press["machine"])
    where = shown.form.rcd_where
    assert where.isVisible() and where.inside.isChecked() and shown.place.is_new
    where.in_front.click()
    assert shown.place.in_front and shown.place.asset_id == press["machine"]
    assert shown.guide.test_object == "main_switch"
    assert list(shown.form.fields) == list(IN_FRONT_OF_PRESS)
    shown.form.fields["upstream_rcd_type"].setEditText("A")
    shown.form.fields["upstream_residual_current"].setEditText("30")
    kept = []
    shown.place_kept.connect(kept.append)
    shown.next.click()
    assert shown.kind == SELECT and kept == [press["machine"]]
    stated = app.db.asset_features(press["machine"])
    assert (stated["upstream_rcd_type"], stated["upstream_residual_current"]) == ("A", "30")
    assert not [row for row in app.db.assets() if row["kind"] == "rcd"]  # no element was made
    assert shown.place.in_front and shown.guide.test_object == "main_switch"


def test_the_answer_can_be_taken_back(qtbot, app, press):
    shown = opened(qtbot, app, press, press["machine"])
    shown.form.rcd_where.in_front.click()
    shown.form.rcd_where.inside.click()
    assert shown.place.is_new and not shown.place.in_front
    assert shown.guide.test_object == "rcd"


def test_a_stated_rcd_in_front_is_taken_without_asking_again(qtbot, app, press):
    app.db.set_asset_features(press["machine"], IN_FRONT_OF_PRESS)
    shown = opened(qtbot, app, press, press["circuit"], "zloop_dc")
    assert shown.place.in_front and shown.form.rcd_where.in_front.isChecked()
    assert shown.form.fields["upstream_rcd_type"].currentText() == "A"


def test_the_question_is_not_asked_where_an_rcd_is_measured_at(qtbot, app, press):
    own = app.db.add_asset(press["customer"], "rcd", "FI", press["machine"])
    shown = opened(qtbot, app, press, own)
    assert not shown.form.rcd_where.isVisible()


def test_a_reading_at_the_supply_is_checked_against_the_rcd_in_front(app, press):
    app.db.set_asset_features(press["machine"], IN_FRONT_OF_PRESS)
    at = datetime(2026, 3, 1, 10, 0)
    reading = MeterMeasurement(uid="u1", function="rcd_time", taken_at=at, verdict=Verdict.PASSED,
                               parameters=(Parameter("rated_residual_current", "300mA"),))
    stored = app.service.receive(press["campaign"], LiveReading(reading, at), press["machine"])
    row = app.db.one("SELECT * FROM measurements WHERE id=?", stored)
    found = SettingCheck(app.db).of_row(row)
    assert [type(item) for item in found] == [Mismatch]
    assert (found[0].used, found[0].expected) == ("300mA", "30 mA")
