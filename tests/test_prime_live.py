# EasyMeasurement - tests/test_prime_live.py
# Push/Print and the link to the instrument. All instrument data here is synthetic.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import time
from datetime import datetime

import pytest

from easymeasurement.devices.base import DeviceError, LinkState
from easymeasurement.devices.profitest_prime.driver import ProfitestPrimeDriver
from easymeasurement.devices.profitest_prime.transport import ALLOWED_COMMANDS
from easymeasurement.devices.simulator import SimulatedMeter
from easymeasurement.model import UNREADABLE_FUNCTION, Verdict

from .prime_helpers import FakeInstrument, event


def wait_until(condition, seconds=3.0):
    deadline = time.monotonic() + seconds
    while not condition():
        assert time.monotonic() < deadline, "Zeitlimit"
        time.sleep(0.005)


@pytest.fixture
def live():
    instrument = FakeInstrument()
    readings, states = [], []
    driver = ProfitestPrimeDriver(channel_factory=lambda: instrument, reconnect_delay_s=0.01)
    driver.open()
    driver.subscribe_live(readings.append, lambda state, text: states.append(state))
    yield driver, instrument, readings, states
    driver.close()


# Push/Print ------------------------------------------------------------------


def test_save_on_the_instrument_reaches_the_callback(live):
    _, instrument, readings, _ = live
    instrument.press_save()
    wait_until(lambda: readings)
    assert readings[0].measurement.function == "riso"
    assert isinstance(readings[0].received_at, datetime)


def test_series_of_measurements_arrives_in_order_and_complete(live):
    _, instrument, readings, _ = live
    for number in range(20):
        instrument.press_save(f"g{number}")
    wait_until(lambda: len(readings) == 20)
    assert [r.measurement.uid for r in readings] == [f"g{n}" for n in range(20)]


def test_each_event_is_acknowledged_after_it_was_delivered(live):
    _, instrument, readings, _ = live
    instrument.press_save()
    wait_until(lambda: "IDNXML:GET:ORDERNO" in instrument.sent)
    assert readings


def test_push_mode_is_entered_once_and_left_on_close():
    instrument = FakeInstrument()
    driver = ProfitestPrimeDriver(channel_factory=lambda: instrument)
    with driver:
        driver.subscribe_live(lambda reading: None)
        assert instrument.push_on
    assert not instrument.push_on
    assert instrument.sent.count("PPXML:ENTER") == 1
    assert instrument.sent.count("PPXML:LEAVE") == 1
    assert instrument.closed


def test_push_mode_is_left_when_the_block_fails():
    instrument = FakeInstrument()
    driver = ProfitestPrimeDriver(channel_factory=lambda: instrument)
    with pytest.raises(RuntimeError):
        with driver:
            driver.subscribe_live(lambda reading: None)
            raise RuntimeError
    assert not instrument.push_on


def test_measurement_arriving_while_leaving_is_still_delivered():
    instrument = FakeInstrument()
    readings = []
    driver = ProfitestPrimeDriver(channel_factory=lambda: instrument)
    driver.open()
    driver.subscribe_live(readings.append)
    instrument.press_save()
    driver.close()
    assert len(readings) == 1


def test_push_mode_left_open_by_a_crash_is_closed_on_connect():
    instrument = FakeInstrument(push_on=True)
    with ProfitestPrimeDriver(channel_factory=lambda: instrument):
        assert not instrument.push_on


def test_no_write_command_ever_leaves_during_push(live):
    driver, instrument, readings, _ = live
    instrument.press_save()
    wait_until(lambda: readings)
    driver.close()
    assert set(instrument.sent) <= ALLOWED_COMMANDS


def test_failing_callback_does_not_stop_later_measurements():
    instrument = FakeInstrument()
    readings, states = [], []

    def on_reading(reading):
        if reading.measurement.uid == "bad":
            raise RuntimeError("Datenträger voll")
        readings.append(reading)

    with ProfitestPrimeDriver(channel_factory=lambda: instrument) as driver:
        driver.subscribe_live(on_reading, lambda state, text: states.append((state, text)))
        instrument.press_save("bad")
        instrument.press_save("good")
        wait_until(lambda: readings)
    assert states[0][0] is LinkState.ERROR
    assert "Datenträger voll" in states[0][1]


def test_unreadable_event_is_delivered_with_its_bytes(live):
    _, instrument, readings, _ = live
    broken = b'<Event name="OnSavePressed"><EventArgs><MEASUREMENT guid="x"</Event>'
    instrument.incoming.put(broken)
    wait_until(lambda: readings)
    measurement = readings[0].measurement
    assert measurement.function == UNREADABLE_FUNCTION
    assert measurement.raw == broken.decode()
    assert measurement.verdict is Verdict.NOT_EVALUATED


def test_event_with_an_unusable_date_is_kept_too(live):
    _, instrument, readings, _ = live
    instrument.incoming.put(event().replace(b"2026-01-01T09:00:00.000", b"kaputt"))
    wait_until(lambda: readings)
    assert readings[0].measurement.function == UNREADABLE_FUNCTION


# Losing the link -------------------------------------------------------------


class Reconnecting:
    def __init__(self, *instruments):
        self.instruments = list(instruments)
        self.failures = 0

    def __call__(self):
        if self.failures:
            self.failures -= 1
            raise DeviceError("Noch nicht wieder da")
        return self.instruments.pop(0)


def _session(factory):
    readings, states = [], []
    driver = ProfitestPrimeDriver(channel_factory=factory, reconnect_delay_s=0.01)
    driver.open()
    driver.subscribe_live(readings.append, lambda state, text: states.append(state))
    return driver, readings, states


def test_dropped_link_is_reported_and_push_resumes():
    first, second = FakeInstrument(), FakeInstrument()
    factory = Reconnecting(first, second)
    driver, readings, states = _session(factory)
    factory.failures = 2
    first.broken = True
    wait_until(lambda: LinkState.CONNECTED in states)
    assert states == [LinkState.LOST, LinkState.CONNECTED]
    assert second.push_on
    second.press_save()
    wait_until(lambda: readings)
    driver.close()
    assert not second.push_on


def test_push_mode_still_on_after_a_dropout_is_not_entered_again():
    first, second = FakeInstrument(), FakeInstrument(push_on=True)
    driver, _, states = _session(Reconnecting(first, second))
    first.broken = True
    wait_until(lambda: LinkState.CONNECTED in states)
    assert "PPXML:ENTER" not in second.sent
    driver.close()


def test_measurements_received_before_the_dropout_are_not_lost():
    first, second = FakeInstrument(), FakeInstrument()
    driver, readings, states = _session(Reconnecting(first, second))
    for number in range(5):
        first.press_save(f"g{number}")
    wait_until(lambda: first.incoming.empty())
    first.broken = True
    wait_until(lambda: LinkState.CONNECTED in states)
    assert len(readings) == 5
    driver.close()


def test_another_instrument_is_not_accepted_after_a_dropout():
    first, stranger = FakeInstrument(), FakeInstrument(serial_no=b"OTHER")
    driver, _, states = _session(Reconnecting(first, stranger))
    first.broken = True
    wait_until(lambda: LinkState.ERROR in states)
    assert "PPXML:ENTER" not in stranger.sent
    driver.close()


def test_closing_during_a_dropout_ends_cleanly():
    first = FakeInstrument()
    factory = Reconnecting(first)
    driver, _, states = _session(factory)
    factory.failures = 10_000
    first.broken = True
    wait_until(lambda: LinkState.LOST in states)
    driver.close()


# Simulator -------------------------------------------------------------------


def test_simulator_behaves_like_the_instrument_in_push_mode():
    meter = SimulatedMeter(seed=1)
    readings = []
    meter.subscribe_live(readings.append)
    pushed = meter.simulate_measurement("u")
    assert readings[0].measurement is pushed
    assert meter.read_measurements() == []  # not kept on the instrument
    meter.unsubscribe_live()
    stored = meter.simulate_measurement("u")
    assert len(readings) == 1
    assert meter.read_measurements() == [stored]
