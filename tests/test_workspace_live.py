# OkeyDocu - tests/test_workspace_live.py
# Values arriving live, and the messages about the link to the instrument.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.devices import Capability, DeviceError, LiveReading
from okeydocu.devices.profitest_prime import transport
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.ui.live_session import LiveSession
from okeydocu.ui.status_badges import BAD, ICON_SIZE, MAX_TEXT_WIDTH

from .workspace_helpers import plan_title, start, with_asset


# Values arriving -------------------------------------------------------------


def test_simulated_push_appears_without_fetching(window, app, monkeypatch):
    with_asset(window, app)
    guided = window.guided
    start(window, monkeypatch, plan_title(window), simulated=True)
    meter = app.devices.driver(app.service.campaign(guided.campaign_id))
    meter.simulate_measurement("u")
    assert len(app.service.measurements(guided.campaign_id)) == 1
    assert "Empfangen" in guided.status.text()


def test_pushed_value_goes_to_the_active_step(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = service.start(asset_id, plan, "P", "T", "simulator", meter)
    step = service.steps(campaign)[0]
    service.confirm_setup(step["id"])
    pushed = []
    meter.subscribe_live(pushed.append)
    meter.simulate_measurement("rlo")
    service.receive(campaign, pushed[0])
    row = service.measurements(campaign, step["id"])[0]
    assert row["assignment"] == "auto"


def test_pushed_value_of_another_function_waits_for_a_decision(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = service.start(asset_id, plan, "P", "T", "simulator", meter)
    service.confirm_setup(service.steps(campaign)[0]["id"])
    pushed = []
    meter.subscribe_live(pushed.append)
    meter.simulate_measurement("riso")
    service.receive(campaign, pushed[0])
    assert service.open_measurements(campaign)[0]["issue"] == "function_mismatch"


def test_same_push_is_stored_once(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = service.start(asset_id, plan, "P", "T", "simulator", meter)
    pushed = []
    meter.subscribe_live(pushed.append)
    meter.simulate_measurement("u")
    service.receive(campaign, pushed[0])
    assert service.receive(campaign, pushed[0]) is None
    assert len(service.measurements(campaign)) == 1


def test_push_keeps_its_evidence(service, asset_id, plan):
    meter = SimulatedMeter()
    campaign = service.start(asset_id, plan, "P", "T", "simulator", meter)
    pushed = []
    meter.subscribe_live(pushed.append)
    measurement = meter.simulate_measurement("u")
    arrived = datetime(2026, 11, 6, 13, 0, 7)
    service.receive(campaign, LiveReading(measurement, arrived))
    row = service.measurements(campaign)[0]
    assert row["received_at"].startswith("2026-11-06T13:00:07")
    assert row["device_serial"] == "SIM-0001"


def test_lost_connection_tells_the_operator_what_to_do(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    page._link_changed(BAD, "Keine Verbindung")
    assert page.link.kind == BAD
    assert "Speichermanager" in page.free.guidance.toolTip()


# Messages --------------------------------------------------------------------


class Unreachable(SimulatedMeter):
    """Looks like a real instrument: connecting happens on a worker thread and fails."""

    capabilities = Capability.READ_STORED | Capability.LIVE_RESULTS

    def open(self):
        raise DeviceError("Bluetooth 00:11:22:33:44:55 [Errno 112]")


def test_unreachable_instrument_gives_a_short_message_without_technical_detail(qtbot):
    session = LiveSession(Unreachable(), 1)
    messages = []
    session.link.connect(lambda kind, text: messages.append((kind, text)))
    session.start()
    qtbot.waitUntil(lambda: any(kind == BAD for kind, _ in messages), timeout=3000)
    session.stop()
    text = dict(messages)[BAD]
    assert text == "Messgerät nicht verbunden"


def test_long_message_cannot_widen_the_window(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    width = window.minimumSizeHint().width()
    window.campaign.link.show_link(BAD, "sehr lange Meldung " * 40)
    assert window.minimumSizeHint().width() <= width + MAX_TEXT_WIDTH + ICON_SIZE + 40


@pytest.mark.parametrize("error", [OSError(112, "Host is down"), TimeoutError("timed out")])
def test_failed_bluetooth_connection_is_explained_without_address_or_errno(monkeypatch, error):
    class FailingSocket:
        def __init__(self, *args):
            pass

        def settimeout(self, seconds):
            pass

        def connect(self, address):
            raise error

        def close(self):
            pass

    monkeypatch.setattr(transport.socket, "socket", FailingSocket)
    with pytest.raises(DeviceError) as caught:
        transport.open_channel("bt:00:11:22:33:44:55")
    assert "00:11" not in str(caught.value)
    assert "112" not in str(caught.value)


def test_a_new_reading_is_selected_and_in_view(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    meter = app.devices.driver(app.service.campaign(page.campaign_id))
    meter.simulate_measurement("u")
    meter.simulate_measurement("rlo")
    table = page.values.table
    assert table.rowCount() == 2
    assert table.currentRow() == 1
    assert page.values.editor.values.rowCount() > 0
