# OkeyDocu - tests/test_campaign_start.py
# A campaign started is open from then on, whether or not its instrument answers.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.__main__ import build_context
from okeydocu.devices import DeviceError, FoundInstrument
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.ui.campaign_dialog import CampaignDialog
from okeydocu.ui.main_window import MainWindow

SIMULATOR = FoundInstrument("simulator", "Simulator")


@pytest.fixture
def app():
    context = build_context()
    context.db.add_asset(context.db.add_customer("Muster AG"), "machine", "Stanze")
    yield context
    context.db.close()


@pytest.fixture
def switched_off(monkeypatch):
    """The instrument stays silent as often as `silent` says, then answers."""
    silent = {"times": 1_000}
    answer = SimulatedMeter.identify

    def identify(self):
        if silent["times"] > 0:
            silent["times"] -= 1
            raise DeviceError("Kein Messgerät gefunden")
        return answer(self)

    monkeypatch.setattr(SimulatedMeter, "identify", identify)
    return silent


@pytest.fixture
def answers(monkeypatch):
    """What the operator answers when the instrument is silent: True tries again."""
    given, replies = [], []
    monkeypatch.setattr("okeydocu.ui.instrument_start.ask_again",
                        lambda _, error: given.append(error) or replies.pop(0))
    return given, replies


def started(qtbot, app, monkeypatch, with_plan: bool):
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [SIMULATOR])
    window = MainWindow(app)
    qtbot.addWidget(window)

    def fill(dialog):
        if with_plan:
            dialog.plan.setCurrentIndex(1)
        else:
            dialog.plan.setCurrentIndex(dialog.plan.findText("Ohne Plan"))
        dialog.source.setCurrentIndex(0)
        dialog.title.setText("Prüfung")
        return 1

    monkeypatch.setattr(CampaignDialog, "exec", fill)
    window.campaign.new_campaign()
    return window


@pytest.mark.parametrize("with_plan", [False, True])
def test_a_silent_instrument_leaves_the_campaign_open(qtbot, app, monkeypatch, switched_off,
                                                     answers, with_plan):
    given, replies = answers
    replies.append(False)
    window = started(qtbot, app, monkeypatch, with_plan)
    campaign = app.service.campaigns()[0]
    assert campaign["status"] == "open" and campaign["driver"] == "simulator"
    assert given == ["Kein Messgerät gefunden"]
    assert app.service.awaits_instrument(campaign["id"])
    assert app.service.clock_checks(campaign["id"]) == []
    assert window.campaign.session is None
    assert window.campaign.campaign_id == campaign["id"]


def test_trying_again_reads_the_instrument_into_the_campaign(qtbot, app, monkeypatch,
                                                            switched_off, answers):
    given, replies = answers
    switched_off["times"] = 2
    replies.extend([True, True])
    window = started(qtbot, app, monkeypatch, False)
    campaign = app.service.campaigns()[0]
    assert len(given) == 2
    assert not app.service.awaits_instrument(campaign["id"])
    assert app.service.identity(campaign["id"]).model
    assert [check["kind"] for check in app.service.clock_checks(campaign["id"])] == ["set"]
    assert window.campaign.live_id == campaign["id"]


def test_resuming_later_brings_the_instrument_in(qtbot, app, monkeypatch, switched_off,
                                                 answers):
    given, replies = answers
    replies.append(False)
    window = started(qtbot, app, monkeypatch, False)
    campaign = app.service.campaigns()[0]["id"]
    switched_off["times"] = 0
    window.campaign.resume()
    assert not app.service.awaits_instrument(campaign)
    assert window.campaign.live_id == campaign
    assert len(given) == 1
