# OkeyDocu - tests/test_voltage_by_conductors.py
# The guided voltage measurement follows the line conductors the element states.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.campaign.expected_voltage import between_lines, expected, misfits
from okeydocu.devices.base import LiveReading
from okeydocu.devices.guide import CONNECT, MEASURE
from okeydocu.devices.profitest_prime.guides import VOLTAGE
from okeydocu.model import MeterMeasurement, Parameter, Quantity, ResultValue, Verdict
from okeydocu.ui.measuring_window import MeasuringWindow

NOW = datetime(2026, 11, 18, 10)


def value(key: str, text: str) -> ResultValue:
    return ResultValue(key, key.upper(), Quantity.parse(text), Verdict.NOT_EVALUATED, "", "")


def reading(function: str, *results, parameters=()) -> LiveReading:
    measurement = MeterMeasurement("x", function, NOW, Verdict.NOT_EVALUATED, results=results,
                                   parameters=tuple(parameters))
    return LiveReading(measurement, NOW)


@pytest.fixture
def machine(app):
    customer = app.db.add_customer("Muster AG")
    return app.db.add_asset(customer, "machine", "Presse")


def opened(qtbot, app, machine, **features) -> MeasuringWindow:
    if features:
        app.db.set_asset_features(machine, features)
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    window = MeasuringWindow(app, campaign, "profitest-prime", "u", machine)
    qtbot.addWidget(window)
    window.show()
    return window


def test_three_line_conductors_lead_to_the_line_voltages_then_the_single_ones():
    suited = VOLTAGE.suited({"line_conductors": "3"}.get)
    assert [guide.function for guide in suited.chain()] == ["u3", "u"]
    assert [lead.terminal for lead in suited.leads] == ["in_l1", "in_l2", "in_l3"]
    assert VOLTAGE.suited({"line_conductors": "1"}.get) is VOLTAGE
    assert VOLTAGE.suited(lambda key: "") is VOLTAGE


def test_the_run_has_nine_stations_for_three_and_six_for_one(qtbot, app, machine):
    three = opened(qtbot, app, machine, line_conductors="3")
    assert three.count == 9 and len(three.bar.chips) == 9
    assert three.bar.names[2] == "Leads to L1, L2 and L3" and three.bar.names[-1] == \
        "Single voltages"
    other = app.db.add_asset(app.db.asset(machine)["customer_id"], "machine", "Säge")
    one = opened(qtbot, app, other, line_conductors="1")
    assert one.count == 6 and one.guide.function == "u"


def test_stating_three_line_conductors_at_the_first_station_changes_the_run(qtbot, app,
                                                                            machine):
    window = opened(qtbot, app, machine)
    assert window.count == 6
    window.form.fields["line_conductors"].setEditText("3")
    window.form.edited.emit()
    assert window.count == 9 and window.guide.function == "u3"
    window.form.fields["line_conductors"].setEditText("1")
    window.form.edited.emit()
    assert window.count == 6 and window.guide.function == "u"


def test_each_part_lays_its_own_leads_and_shows_its_own_result(qtbot, app, machine):
    window = opened(qtbot, app, machine, line_conductors="3", n_conductor="with N")
    window.show_reading(reading("u", value("u", "231V"), parameters=[]))
    window.go(5)
    assert window.kind == MEASURE and window.guide.function == "u3"
    assert window.reading is None
    window.show_reading(reading("u3", value("u_l1l2", "401V"), value("u_l2l3", "399V")))
    assert "401V" in window.step_text.text()
    window.go(6)
    assert window.kind == CONNECT and window.guide.function == "u"
    assert [lead.terminal for lead in window.bench.guide.leads] == ["pe", "in_l1", "in_n"]
    window.go(8)
    assert window.reading.measurement.function == "u" and "231V" in window.step_text.text()
    window.go(5)
    assert window.bench.guide.function == "u3" and window.bench.progress == 3.0


def test_without_n_only_the_lead_to_n_stays_away(qtbot, app, machine):
    window = opened(qtbot, app, machine, line_conductors="3", n_conductor="without N")
    lines, single = dict.fromkeys(window.owners)
    assert [lead.probe for lead in lines.leads] == ["L (L1)", "PE (L2)", "N (L3)"]
    assert [lead.terminal for lead in single.leads] == ["pe", "in_l1"]


def test_three_probes_side_by_side_get_their_markings_in_two_lines(qtbot, app, machine):
    window = opened(qtbot, app, machine, line_conductors="3")
    window.go(2)
    window.bench.grab()
    assert window.bench._crowded(window.bench._side(-1))
    window.go(6)
    window.bench.grab()
    assert not window.bench._crowded(window.bench._side(-1))


def test_what_to_expect_between_two_conductors():
    assert expected("L1-L2") == 400
    assert expected("L-PE") == pytest.approx(230.9, abs=0.1)
    assert expected("L3-N") == pytest.approx(230.9, abs=0.1)
    assert expected("N-PE") is None
    assert between_lines("3", "") == 400 and between_lines("3", "690 V") == 690
    assert between_lines("1", "230 V") == pytest.approx(398.4, abs=0.1)


def test_only_voltages_off_by_more_than_a_tenth_are_named():
    lines = reading("u3", value("u_l1l2", "232V"), value("u_l2l3", "385V"),
                    value("u_l3l1", "441V"), value("f", "50.0Hz")).measurement
    assert [(label, wanted) for label, _, wanted in misfits(lines)] == [
        ("U_L1L2", 400), ("U_L3L1", 400)]
    single = reading("u", value("u", "398V"),
                     parameters=[Parameter("conductor", "L1-PE")]).measurement
    assert [raw for _, raw, _ in misfits(single)] == ["398V"]
    assert misfits(reading("u", value("u", "3V"),
                           parameters=[Parameter("conductor", "N-PE")]).measurement) == []


def test_the_measure_station_warns_of_a_voltage_that_does_not_fit(qtbot, app, machine):
    window = opened(qtbot, app, machine, line_conductors="3")
    window.go(5)
    window.show_reading(reading("u3", value("u_l1l2", "232V"), value("u_l2l3", "400V")))
    text = window.step_text.text()
    assert "U_L1L2 232V" in text and "etwa 400 V" in text and "U_L2L3 400V:" not in text
