# OkeyDocu - tests/test_instrument_finding.py
# Finding instruments, first-time pairing, and starting wherever the switch stands.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import subprocess
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from okeydocu.devices import DeviceBlocked, DeviceError, FoundInstrument
from okeydocu.devices.profitest_prime import discovery, pairing
from okeydocu.devices.simulator import SimulatedMeter

from .prime_helpers import ADDRESS


def usb_port(vid, pid, device):
    return SimpleNamespace(vid=vid, pid=pid, device=device)


@pytest.fixture
def usb(monkeypatch):
    ports = []
    monkeypatch.setattr("serial.tools.list_ports.comports", lambda: ports)
    return ports


@pytest.fixture
def paired(monkeypatch):
    lines = []

    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args, 0, stdout="\n".join(lines))

    monkeypatch.setattr(discovery.subprocess, "run", run)
    return lines


# Finding ---------------------------------------------------------------------


def test_instrument_is_recognised_on_usb_by_its_ids(usb, paired):
    usb += [usb_port(None, None, "/dev/ttyS0"), usb_port(0x1CD7, 0x0117, "/dev/ttyACM3"),
            usb_port(0x1234, 0x0117, "/dev/ttyACM1")]
    assert discovery.find_instruments() == [
        FoundInstrument("profitest-prime", "PROFITEST PRIME (USB)", "/dev/ttyACM3")
    ]


def test_paired_instrument_is_listed_even_while_it_is_off(usb, paired):
    paired += [f"Device {ADDRESS} PROFITEST", "Device AA:BB:CC:DD:EE:FF Maus"]
    assert discovery.find_instruments() == [
        FoundInstrument("profitest-prime", "PROFITEST PRIME (Bluetooth)", f"bt:{ADDRESS}")
    ]


def test_cable_comes_first(usb, paired):
    usb.append(usb_port(0x1CD7, 0x0117, "/dev/ttyACM0"))
    paired.append(f"Device {ADDRESS} PROFITEST")
    assert [i.port for i in discovery.find_instruments()] == ["/dev/ttyACM0", f"bt:{ADDRESS}"]


def test_missing_bluetooth_tools_are_no_error(usb, monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("bluetoothctl")

    monkeypatch.setattr(discovery.subprocess, "run", missing)
    assert discovery.find_instruments() == []


def test_nothing_found_says_what_to_do(usb, paired):
    with pytest.raises(DeviceError, match="einrichten"):
        discovery.open_any()


def test_connection_falls_back_from_cable_to_bluetooth(usb, paired, monkeypatch):
    usb.append(usb_port(0x1CD7, 0x0117, "/dev/ttyACM0"))
    paired.append(f"Device {ADDRESS} PROFITEST")
    opened = []

    def open_channel(port):
        opened.append(port)
        if port.startswith("/dev"):
            raise DeviceError("Port belegt")
        return "kanal"

    monkeypatch.setattr(discovery, "open_channel", open_channel)
    assert discovery.open_any() == "kanal"
    assert opened == ["/dev/ttyACM0", f"bt:{ADDRESS}"]


# Pairing ---------------------------------------------------------------------


FAKE_BLUETOOTHCTL = """
import sys
for line in sys.stdin:
    line = line.strip()
    if line == "scan on":
        print("[NEW] Device AA:AA:AA:AA:AA:AA Fremdgeraet", flush=True)
        print("[\\x1b[0;92mNEW\\x1b[0m] Device 00:11:22:33:44:55 PROFITEST".replace("\\x1b[0;92m", "").replace("\\x1b[0m", ""), flush=True)
    elif line.startswith("pair "):
        print("Request PIN code", flush=True)
        print("[agent] Enter PIN code: ", flush=True)
    elif line == "1234":
        print("[CHG] Paired: yes", flush=True)
        print("Pairing successful", flush=True)
    elif line == "9999":
        print("Failed to pair: org.bluez.Error.AuthenticationFailed", flush=True)
    elif line.startswith("trust "):
        print("TRUSTED " + line, file=open(sys.argv[1], "w"), flush=True)
    elif line == "quit":
        break
"""


def fake_tool(tmp_path, body=FAKE_BLUETOOTHCTL):
    script = tmp_path / "bluetoothctl.py"
    script.write_text(body, encoding="utf-8")
    marker = tmp_path / "trusted"
    return (sys.executable, str(script), str(marker)), marker


def test_pairing_finds_answers_the_pin_and_trusts(tmp_path):
    command, marker = fake_tool(tmp_path)
    steps = []
    address = pairing.pair_instrument("1234", steps.append, command)
    assert address == ADDRESS
    assert len(steps) == 2
    assert ADDRESS in marker.read_text()


def test_wrong_pin_is_reported(tmp_path):
    command, marker = fake_tool(tmp_path)
    with pytest.raises(pairing.PairingFailed, match="PIN"):
        pairing.pair_instrument("9999", command=command)
    assert not marker.exists()


def test_instrument_out_of_sight_is_explained(tmp_path):
    command, _ = fake_tool(tmp_path, "import sys\nfor line in sys.stdin:\n    pass\n")
    with pytest.raises(pairing.PairingFailed, match="sichtbar"):
        pairing.pair_instrument(command=command, scan_timeout_s=0.3)


def test_missing_tool_is_reported(tmp_path):
    with pytest.raises(pairing.PairingFailed):
        pairing.pair_instrument(command=("/nonexistent/bluetoothctl",), scan_timeout_s=0.3)


# Starting anywhere -----------------------------------------------------------


class BlockedMeter(SimulatedMeter):
    """The rotary switch is not on Setup."""

    blocked = True

    def read_measurements(self):
        if self.blocked:
            raise DeviceBlocked("Fehler 402")
        return super().read_measurements()


def start(service, asset_id, plan, meter):
    return service.start(asset_id, plan, "Prüfung", "Prüfer", "simulator", meter)


def test_campaign_starts_without_the_switch_on_setup(service, asset_id, plan):
    campaign = start(service, asset_id, plan, BlockedMeter(clock_skew_s=600))
    assert service.campaign(campaign)["stored_since"]
    assert service.clock_status(campaign).text.startswith("Geräteuhr synchron")


def test_starting_does_not_read_the_instruments_memory(service, asset_id, plan, monkeypatch):
    meter = SimulatedMeter()

    def must_not_run():
        raise AssertionError("15 s Abruf beim Start")

    monkeypatch.setattr(meter, "read_measurements", must_not_run)
    start(service, asset_id, plan, meter)


def test_old_readings_stay_out_though_the_memory_was_not_read(service, asset_id, plan):
    meter = BlockedMeter()
    meter.simulate_measurement("u", at=datetime.now() - timedelta(minutes=5))
    campaign = start(service, asset_id, plan, meter)
    meter.blocked = False
    assert service.collect(campaign, meter)["added"] == 0


def test_readings_after_the_start_are_collected(service, asset_id, plan):
    meter = BlockedMeter()
    campaign = start(service, asset_id, plan, meter)
    meter.blocked = False
    meter.simulate_measurement("u", at=datetime.now() + timedelta(seconds=5))
    assert service.collect(campaign, meter)["added"] == 1


def test_an_instrument_that_is_gone_still_stops_the_start(service, asset_id, plan, monkeypatch):
    meter = SimulatedMeter()

    def gone():
        raise DeviceError("Keine Antwort")

    monkeypatch.setattr(meter, "identify", gone)
    with pytest.raises(DeviceError):
        start(service, asset_id, plan, meter)
