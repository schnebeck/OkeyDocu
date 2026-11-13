# OkeyDocu - tests/test_prime_selector.py
# Reading the rotary switch, text replies beside events, and how Push/Print ends.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.devices import Capability, DeviceError, SelectorPosition
from okeydocu.devices.profitest_prime.driver import ProfitestPrimeDriver
from okeydocu.devices.profitest_prime.framing import EVENT, REPLY, TEXT, FrameSplitter
from okeydocu.devices.profitest_prime.push_print import PUSH_LEFT_ON
from okeydocu.devices.profitest_prime.selector import selector_position
from okeydocu.l10n import tr
from okeydocu.devices.profitest_prime.transport import (
    ALLOWED_COMMANDS,
    TEXT_COMMANDS,
    ForbiddenCommand,
    PrimeTransport,
)
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.vocabulary import function_keys

from .prime_helpers import FakeInstrument, event, reply


@pytest.fixture
def instrument():
    return FakeInstrument()


@pytest.fixture
def driver(instrument):
    meter = ProfitestPrimeDriver(channel_factory=lambda: instrument, reconnect_delay_s=0.01)
    meter.open()
    yield meter
    meter.close()


# Text lines ------------------------------------------------------------------


def test_a_text_line_is_a_frame_of_its_own():
    assert FrameSplitter().feed(b"0;15\n") == [(TEXT, b"0;15")]


def test_a_text_line_waits_for_its_end():
    splitter = FrameSplitter()
    assert splitter.feed(b"0;1") == []
    assert splitter.feed(b"5\r\n") == [(TEXT, b"0;15")]


def test_a_text_line_between_frames_loses_nothing():
    frames = FrameSplitter().feed(event() + b"\n0;15\n" + reply("X"))
    assert [kind for kind, _ in frames] == [EVENT, TEXT, REPLY]


def test_a_line_in_front_of_an_event_does_not_take_the_event_with_it():
    frames = FrameSplitter().feed(b"0;15\n" + event())
    assert [kind for kind, _ in frames] == [TEXT, EVENT]


def test_figures_inside_a_frame_stay_in_the_frame():
    frame = b"<Event a='1'>\n0;15\n</Event>"
    assert FrameSplitter().feed(frame) == [(EVENT, frame)]


def test_only_listed_text_commands_are_sent(instrument):
    with PrimeTransport(instrument) as transport, pytest.raises(ForbiddenCommand):
        transport.query_text("SYS:GET:LEDS")
    assert instrument.sent == []


def test_text_commands_only_read():
    assert TEXT_COMMANDS == {"SYS:GET:ROTATIONWHEEL"}
    assert not TEXT_COMMANDS & ALLOWED_COMMANDS


def test_a_line_left_over_from_a_timeout_is_not_taken_for_the_answer(instrument):
    with PrimeTransport(instrument) as transport:
        transport.start()
        instrument.incoming.put(b"0;99\n")
        while transport._lines.empty():
            pass
        assert transport.query_text("SYS:GET:ROTATIONWHEEL") == "15"


def test_an_error_code_in_a_text_line_is_reported(instrument):
    instrument.wheel = b"200\n"
    with PrimeTransport(instrument) as transport, pytest.raises(DeviceError, match="200"):
        transport.query_text("SYS:GET:ROTATIONWHEEL")


def test_no_answer_ends_in_an_error_and_not_in_a_hang(instrument):
    instrument.wheel = b""
    with PrimeTransport(instrument) as transport, pytest.raises(DeviceError, match="Keine Antwort"):
        transport.query_text("SYS:GET:ROTATIONWHEEL", timeout_s=0.05)


# Positions -------------------------------------------------------------------


def test_every_function_named_by_a_position_exists():
    for value in range(12, 33):
        assert selector_position(value).functions <= set(function_keys())


@pytest.mark.parametrize("value", [11, 36])
def test_an_unknown_position_has_no_label(value):
    assert selector_position(value) == SelectorPosition()


@pytest.mark.parametrize("value, label", [
    (32, "Auto"), (33, "Setup"), (34, "Batteriezustand"), (35, "OFF"),
])
def test_the_last_positions_are_named_as_printed_and_rule_out_nothing(value, label):
    position = selector_position(value)
    assert position.label == label and not position.functions
    assert not position.rules_out("riso")


def test_a_position_rules_out_what_it_cannot_measure():
    assert selector_position(15).rules_out("rlo")
    assert not selector_position(15).rules_out("riso")


@pytest.mark.parametrize("value", [29, 30, 31, 32])
def test_positions_holding_a_list_rule_out_nothing(value):
    assert not selector_position(value).rules_out("riso")


@pytest.mark.parametrize("value", [20, 21, 22, 23])
def test_every_loop_position_serves_a_loop_step(value):
    assert not selector_position(value).rules_out("zloop")


def test_the_driver_reports_the_switch(driver):
    assert Capability.SELECTOR in driver.capabilities
    assert driver.read_selector().label == "RISO"


def test_the_switch_can_be_read_during_push(driver, instrument):
    driver.subscribe_live(lambda reading: None)
    assert driver.read_selector().label == "RISO"
    assert "SYS:GET:ROTATIONWHEEL" in instrument.sent


def test_nonsense_from_the_instrument_is_an_error(driver, instrument):
    instrument.wheel = b"0;kaputt\n"
    with pytest.raises(DeviceError, match="Schalterstellung"):
        driver.read_selector()


def test_the_simulator_follows_the_last_measurement():
    meter = SimulatedMeter()
    with pytest.raises(DeviceError):
        meter.read_selector()
    meter.simulate_measurement("riso")
    assert meter.read_selector().label == "RISO"
    assert meter.read_selector().rules_out("rlo")


# How Push/Print ends ---------------------------------------------------------


@pytest.mark.parametrize("code, text", [(500, "drei Verbindungen"), (403, "belegt")])
def test_a_refused_push_says_what_is_wrong(driver, instrument, code, text):
    instrument.refuse_push = code
    with pytest.raises(DeviceError, match=text):
        driver.subscribe_live(lambda reading: None)


def test_a_clean_end_leaves_no_warning(driver):
    driver.subscribe_live(lambda reading: None)
    driver.unsubscribe_live()
    assert driver.stop_warning == ""


def test_an_end_without_signing_off_warns(driver, instrument):
    driver.subscribe_live(lambda reading: None)
    instrument.broken = True
    driver.unsubscribe_live()
    assert driver.stop_warning == tr(PUSH_LEFT_ON)


def test_coming_back_on_another_connection_warns(instrument):
    class OtherLink(FakeInstrument):
        pass

    links = [instrument, OtherLink()]
    meter = ProfitestPrimeDriver(channel_factory=lambda: links.pop(0), reconnect_delay_s=0.01)
    meter.open()
    states = []
    meter.subscribe_live(lambda reading: None, lambda state, text: states.append(state))
    instrument.broken = True
    while len(states) < 2:
        pass
    assert meter.stop_warning == tr(PUSH_LEFT_ON)
    meter.close()
