# OkeyDocu - tests/test_instrument_choice.py
# Choosing an instrument by name, and a window that stays alive during its work.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import threading
import time

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QPushButton

from okeydocu.__main__ import build_context
from okeydocu.devices import DeviceError, FoundInstrument
from okeydocu.devices.profitest_prime import pairing
from okeydocu.devices.profitest_prime.info import DRIVER as PRIME_DRIVER
from okeydocu.devices.simulator import SimulatedMeter
from okeydocu.ui.campaign_dialog import CampaignDialog
from okeydocu.ui.common import run_busy
from okeydocu.ui.instrument_setup import InstrumentSetupOverlay
from okeydocu.ui.main_window import MainWindow
from okeydocu.ui.settings_dialog import SettingsOverlay

from .prime_helpers import ADDRESS


# Choosing --------------------------------------------------------------------


@pytest.fixture
def app():
    context = build_context()
    context.db.add_asset(context.db.add_customer("Muster AG"), "installation", "Halle 1")
    yield context
    context.db.close()


def labels(dialog):
    return [dialog.source.itemText(i) for i in range(dialog.source.count())]


PRIME = FoundInstrument("profitest-prime", "PROFITEST PRIME (Bluetooth)", f"bt:{ADDRESS}")


def test_dialog_asks_for_an_instrument_not_for_a_port(qtbot, app):
    dialog = CampaignDialog(app, plans=[])
    qtbot.addWidget(dialog)
    assert not hasattr(dialog, "port")


def test_known_instrument_is_already_chosen(qtbot, app, plan, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [PRIME])
    dialog = CampaignDialog(app, plans=[plan])
    qtbot.addWidget(dialog)
    assert dialog.source.currentData() == PRIME
    assert labels(dialog) == ["PROFITEST PRIME (Bluetooth)", "Simulator (Zufallswerte)"]


def test_no_address_is_ever_shown(qtbot, app, plan, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [PRIME])
    dialog = CampaignDialog(app, plans=[plan])
    qtbot.addWidget(dialog)
    assert not any(ADDRESS in text or "/dev" in text for text in labels(dialog))


def test_instrument_plugged_in_later_appears(qtbot, app, plan, monkeypatch):
    dialog = CampaignDialog(app, plans=[plan])
    qtbot.addWidget(dialog)
    assert labels(dialog) == ["Simulator (Zufallswerte)"]
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [PRIME])
    dialog._fill_sources()
    assert labels(dialog)[0] == "PROFITEST PRIME (Bluetooth)"


def test_refreshing_keeps_the_operators_choice(qtbot, app, plan, monkeypatch):
    usb = FoundInstrument("profitest-prime", "PROFITEST PRIME (USB)", "/dev/ttyACM0")
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [PRIME])
    dialog = CampaignDialog(app, plans=[plan])
    qtbot.addWidget(dialog)
    dialog.source.setCurrentIndex(1)
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [usb, PRIME])
    dialog._fill_sources()
    assert dialog.source.currentText() == "Simulator (Zufallswerte)"


def test_campaign_without_a_plan_can_be_typed_in(qtbot, app):
    dialog = CampaignDialog(app)
    qtbot.addWidget(dialog)
    assert dialog.plan.currentText() == "Ohne Plan"
    assert labels(dialog) == ["Manuelle Eingabe"]


def test_plan_can_be_left_out_and_the_choice_follows(qtbot, app, plan, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.campaign_dialog.find_instruments", lambda: [PRIME])
    dialog = CampaignDialog(app, plans=[plan])
    qtbot.addWidget(dialog)
    dialog.plan.setCurrentIndex(dialog.plan.findText("Ohne Plan"))
    assert labels(dialog) == ["PROFITEST PRIME (Bluetooth)", "Manuelle Eingabe"]
    assert dialog.source.currentData() == PRIME


def _new_campaign(window, plan_text, monkeypatch):
    def fill(dialog):
        dialog.plan.setCurrentIndex(dialog.plan.findText(plan_text))
        dialog.title.setText("Prüfung")
        return 1

    monkeypatch.setattr(CampaignDialog, "exec", fill)
    window.campaign.new_campaign()


def test_campaign_with_a_plan_opens_the_guided_steps(qtbot, app, monkeypatch):
    window = MainWindow(app)
    qtbot.addWidget(window)
    _new_campaign(window, window.guided.plans[0].label, monkeypatch)
    assert window.campaign.current_work() is window.guided
    assert window.guided.campaign_id is not None


def test_campaign_without_a_plan_opens_the_list(qtbot, app, monkeypatch):
    window = MainWindow(app)
    qtbot.addWidget(window)
    _new_campaign(window, "Ohne Plan", monkeypatch)
    assert window.campaign.current_work() is window.campaign.free
    campaign = app.service.campaigns()[0]
    assert campaign["plan_key"] == "" and campaign["driver"] == "manual"


def test_setting_up_is_not_part_of_starting_a_campaign(qtbot, app, plan):
    dialog = CampaignDialog(app, plans=[plan])
    qtbot.addWidget(dialog)
    assert not [b for b in dialog.findChildren(QPushButton) if "einrichten" in b.text()]


def test_configuration_is_reached_from_the_menu(qtbot, app, monkeypatch):
    opened = []
    monkeypatch.setattr(SettingsOverlay, "exec", lambda self: opened.append(self))
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.settings_action.trigger()
    assert len(opened) == 1


def test_configuration_lists_instruments_by_name(qtbot, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.settings_dialog.find_instruments", lambda: [PRIME])
    dialog = SettingsOverlay()
    qtbot.addWidget(dialog)
    assert dialog.instruments.item(0).text() == "PROFITEST PRIME (Bluetooth)"
    assert dialog.hint.isHidden()


def test_configuration_says_so_when_there_is_no_instrument(qtbot):
    dialog = SettingsOverlay()
    qtbot.addWidget(dialog)
    assert dialog.instruments.count() == 0
    assert not dialog.hint.isHidden()


def test_instrument_appears_right_after_setting_it_up(qtbot, monkeypatch):
    dialog = SettingsOverlay()
    qtbot.addWidget(dialog)
    monkeypatch.setattr(InstrumentSetupOverlay, "exec", lambda self: 1)
    monkeypatch.setattr("okeydocu.ui.settings_dialog.find_instruments", lambda: [PRIME])
    dialog.pairing_buttons[PRIME_DRIVER.key].click()
    assert dialog.instruments.count() == 1


def test_setup_dialog_reports_success_and_closes(qtbot, monkeypatch):
    monkeypatch.setattr(pairing, "pair_instrument", lambda pin, progress: ADDRESS)
    dialog = InstrumentSetupOverlay(PRIME_DRIVER.pairing)
    qtbot.addWidget(dialog)
    with qtbot.waitSignal(dialog.paired, timeout=3000):
        dialog.start()
    assert dialog.accepted and dialog.port == f"bt:{ADDRESS}"


def test_setup_dialog_shows_a_failure_and_stays_open(qtbot, monkeypatch):
    def fail(pin, progress):
        raise pairing.PairingFailed("nicht gefunden")

    monkeypatch.setattr(pairing, "pair_instrument", fail)
    dialog = InstrumentSetupOverlay(PRIME_DRIVER.pairing)
    qtbot.addWidget(dialog)
    dialog.show()
    dialog.start()
    qtbot.waitUntil(lambda: dialog.status.text() == "nicht gefunden", timeout=3000)
    assert dialog.start_button.isEnabled()
    dialog.worker.wait()


# The window stays alive ------------------------------------------------------


def test_slow_instrument_work_does_not_block_the_window(qtbot, app, monkeypatch):
    """The event loop keeps running while the work goes on."""
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    beats = []
    timer = QTimer(interval=10)
    timer.timeout.connect(lambda: beats.append(1))
    timer.start()
    run_busy(window, "Warte …", lambda: time.sleep(0.3))
    timer.stop()
    assert len(beats) >= 10
    assert window.isEnabled()


def test_work_runs_outside_the_gui_thread(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)
    assert run_busy(window, "Warte …", threading.current_thread) is not threading.current_thread()


def test_error_during_the_work_reaches_the_caller_and_frees_the_window(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)

    def fail():
        raise DeviceError("Keine Antwort")

    with pytest.raises(DeviceError, match="Keine Antwort"):
        run_busy(window, "Warte …", fail)
    assert window.isEnabled()


def test_failed_start_leaves_no_campaign_and_says_why(qtbot, app, plan, monkeypatch):
    errors = []
    monkeypatch.setattr("okeydocu.ui.guided_actions.show_error", lambda _, text: errors.append(text))
    monkeypatch.setattr(SimulatedMeter, "identify", lambda self: (_ for _ in ()).throw(
        DeviceError("Kein Messgerät gefunden")))
    window = MainWindow(app)
    qtbot.addWidget(window)
    assert window.guided.start_campaign(1, plan, "T", "P", "simulator") is None
    assert errors == ["Kein Messgerät gefunden"]
    assert app.service.campaigns() == []
