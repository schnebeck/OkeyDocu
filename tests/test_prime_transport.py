# EasyMeasurement - tests/test_prime_transport.py
# Framing, commands and events on the link to the instrument. All data is synthetic.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import errno
import random
from datetime import datetime

import pytest

from easymeasurement.devices.base import DeviceError
from easymeasurement.devices.profitest_prime.parser import parse_event
from easymeasurement.devices.profitest_prime.transport import (
    ALLOWED_COMMANDS,
    EVENT,
    PUSH_COMMANDS,
    REPLY,
    FrameSplitter,
    LinkLost,
    PrimeTransport,
    RfcommChannel,
    open_channel,
)
from easymeasurement.model import Verdict

from .prime_helpers import FakeInstrument, OHM, boolean_reply, empty_reply, event, reply


# Framing ---------------------------------------------------------------------


def test_stream_comes_apart_correctly_however_it_is_cut():
    stream = (
        reply("IDNXML:GET:TYPE", b"PROFITEST PRIME") + event("a") + empty_reply("PPXML:ENTER")
        + event("b") + event("c") + boolean_reply("PPXML:IS:ON", True)
    )
    for seed in range(200):
        rng = random.Random(seed)
        splitter, position, frames = FrameSplitter(), 0, []
        while position < len(stream):
            size = rng.randint(1, 60)
            frames += splitter.feed(stream[position:position + size])
            position += size
        assert [kind for kind, _ in frames] == [REPLY, EVENT, REPLY, EVENT, EVENT, REPLY]


def test_event_right_behind_a_reply_in_one_read_is_kept():
    frames = FrameSplitter().feed(reply("IDNXML:GET:ORDERNO", b"M") + event())
    assert [kind for kind, _ in frames] == [REPLY, EVENT]


def test_inner_event_args_do_not_start_a_frame():
    frame = FrameSplitter().feed(event())[0][1]
    assert frame.startswith(b"<Event ")


def test_event_in_the_middle_of_a_reply_leaves_both_whole():
    whole = reply("IDNXML:GET:TYPE", b"PROFITEST PRIME")
    frames = FrameSplitter().feed(whole[:40] + event() + whole[40:])
    assert frames == [(EVENT, event()), (REPLY, whole.rstrip())]


def test_noise_before_a_frame_does_not_pile_up():
    splitter = FrameSplitter()
    for _ in range(3):
        splitter.feed(b"noise" + reply("IDNXML:GET:TYPE"))
    assert splitter._buffer == b""


# Commands --------------------------------------------------------------------


def test_replies_without_content_are_understood():
    assert PrimeTransport._decode("PPXML:ENTER", empty_reply("PPXML:ENTER")) == b""


def test_boolean_reply_is_understood():
    raw = boolean_reply("PPXML:IS:ON", False)
    assert PrimeTransport._decode("PPXML:IS:ON", raw) == b"false"


def test_late_reply_to_an_earlier_command_is_ignored():
    instrument = FakeInstrument()
    with PrimeTransport(instrument) as transport:
        instrument.incoming.put(reply("IDNXML:GET:TYPE", b"alt"))
        assert transport.query("IDNXML:GET:ORDERNO") == b"M506A"


def test_event_during_a_command_waits_for_its_turn():
    instrument = FakeInstrument()
    with PrimeTransport(instrument) as transport:
        instrument.press_save()
        assert transport.query("IDNXML:GET:ORDERNO") == b"M506A"
        assert transport.events.get(timeout=1)[1] == event()


def test_lost_link_ends_a_waiting_command():
    instrument = FakeInstrument()
    with PrimeTransport(instrument) as transport:
        transport.start()
        instrument.broken = True
        with pytest.raises(LinkLost):
            transport.query("IDNXML:GET:ORDERNO")


def test_allowed_commands_are_read_commands_and_push_mode():
    assert PUSH_COMMANDS == {"PPXML:IS:ON", "PPXML:ENTER", "PPXML:LEAVE"}
    for command in ALLOWED_COMMANDS:
        assert ":SET" not in command
        assert not command.startswith(("FLASHER", "LAUNCHER", "FS:", "SYS:", "CONFIG"))


@pytest.mark.parametrize("port", ["bt:nonsense", "bt:00:11:22:33:44", "bt:00:11:22:33:44:55/x"])
def test_bad_bluetooth_address_is_refused(port):
    with pytest.raises(DeviceError, match="Bluetooth address"):
        open_channel(port)


class FakeSocket:
    def __init__(self, failure):
        self.failure = failure

    def recv(self, size):
        if self.failure is None:
            return b""
        raise self.failure


def rfcomm(failure):
    channel = RfcommChannel.__new__(RfcommChannel)
    channel._socket = FakeSocket(failure)
    return channel


def test_quiet_bluetooth_link_is_not_a_failure():
    assert rfcomm(TimeoutError("timed out")).read() == b""


def test_vanished_radio_link_is_noticed():
    with pytest.raises(OSError):
        rfcomm(TimeoutError(errno.ETIMEDOUT, "Connection timed out")).read()


@pytest.mark.parametrize("code", [errno.ECONNRESET, errno.EHOSTDOWN, errno.ECONNABORTED])
def test_broken_bluetooth_link_is_noticed(code):
    with pytest.raises(OSError):
        rfcomm(OSError(code, "weg")).read()


def test_closed_bluetooth_link_is_noticed():
    with pytest.raises(ConnectionError):
        rfcomm(None).read()


# Events ----------------------------------------------------------------------


def test_event_is_parsed_despite_its_namespace():
    measurement = parse_event(event())
    assert measurement.function == "riso"
    assert measurement.verdict is Verdict.PASSED
    riso = measurement.result("riso")
    assert riso.quantity.base_value == pytest.approx(1.2e9)
    assert riso.quantity.base_unit == "Ω"
    assert riso.quantity.qualifier == ">"
    assert riso.lower_limit == f">1.00M{OHM}"


def test_time_comes_from_testdate_not_from_the_faulty_timestamp():
    assert parse_event(event()).taken_at == datetime(2026, 1, 1, 9, 0, 0)


def test_event_keeps_the_record_as_it_came():
    assert parse_event(event()).raw == event().decode()
