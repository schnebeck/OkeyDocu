# OkeyDocu - tests/test_instrument_tests.py
# Testing an instrument, keeping each run, and its history with the campaigns it measured in.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import date, datetime, timedelta

from okeydocu.devices import Capability, DeviceError, SelectorPosition
from okeydocu.devices.instrument_check import FAILED, NOTE, OK, run_checks
from okeydocu.model import DeviceIdentity

IDENTITY = DeviceIdentity("Hersteller", "Modell", "TEST0001", "01.02.03",
                          calibrated_on=date(2025, 3, 1), recalibration_due=date(2026, 9, 1))


class _Instrument:
    capabilities = (Capability.CLOCK | Capability.SELECTOR | Capability.LIVE_RESULTS
                    | Capability.TEXTS)

    def __init__(self, skew_s=0, unreachable=False):
        self.skew, self.unreachable, self.pushing = skew_s, unreachable, None
        self.closed = False

    def open(self):
        if self.unreachable:
            raise DeviceError("Messgerät nicht erreichbar.")

    def close(self):
        self.closed = True

    def identify(self):
        return IDENTITY

    def read_clock(self):
        return datetime.now() + timedelta(seconds=self.skew)

    def read_selector(self):
        return SelectorPosition("Setup", frozenset())

    def subscribe_live(self, on_reading, on_state=None):
        self.pushing = True

    def unsubscribe_live(self):
        self.pushing = False


def test_every_part_is_tried_once_and_nothing_is_set(app):
    instrument = _Instrument()
    run = run_checks(instrument, date(2026, 5, 4))
    assert [(c.key, c.state) for c in run.checks] == [
        ("connect", OK), ("identity", OK), ("calibration", OK), ("clock", OK),
        ("selector", OK), ("push", OK)]
    assert run.ready and instrument.pushing is False and instrument.closed


def test_a_clock_off_or_an_overdue_calibration_is_noted_not_failed():
    run = run_checks(_Instrument(skew_s=-60), date(2026, 10, 1))
    states = {c.key: (c.state, c.detail) for c in run.checks}
    assert states["clock"][0] == NOTE and "\u221260 s" in states["clock"][1]
    assert states["calibration"] == (NOTE, "seit 01.09.2026 überfällig")
    assert run.ready and round(run.clock_offset_s) == -60


def test_without_a_connection_nothing_else_is_tried():
    run = run_checks(_Instrument(unreachable=True), date(2026, 5, 4))
    assert [(c.key, c.state) for c in run.checks] == [("connect", FAILED)]
    assert not run.ready


def test_the_history_holds_tests_and_campaigns_newest_first(app):
    test_id = app.service.save_instrument_test("prime", "USB",
                                               run_checks(_Instrument(), date(2026, 5, 4)))
    earlier = (datetime.now() - timedelta(hours=1)).isoformat(timespec="seconds")
    app.db.execute("UPDATE instrument_tests SET tested_at=? WHERE id=?", earlier, test_id)
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    app.service.create(asset, "Wiederholungsprüfung", "Prüfer", None, "profitest-prime",
                       IDENTITY, 0.0, offset_before_s=-6.0)
    app.service.create(asset, "Von Hand", "Prüfer")  # names no instrument
    assert app.service.known_instruments() == [("TEST0001", "Modell")]
    history = app.service.instrument_history("TEST0001")
    assert [entry.kind for entry in history] == ["campaign", "test"]
    campaign, test = history
    assert campaign.clock_offset_s == -6.0 and campaign.firmware == "01.02.03"
    assert test.ready and test.title == "Test über USB" and len(test.checks) == 6


def test_the_test_window_runs_by_itself_and_keeps_the_run(app, qtbot, monkeypatch):
    from okeydocu.ui.instrument_test import InstrumentTestOverlay
    monkeypatch.setattr(app.devices, "new_driver", lambda key, port="": _Instrument())
    overlay = InstrumentTestOverlay(app, "prime", "bt:00:11:22:33:44:55", "PRIME (Bluetooth)")
    qtbot.addWidget(overlay)
    qtbot.waitUntil(lambda: overlay.run is not None, timeout=3000)
    assert overlay.ok_button.isEnabled() and "Bereit" in overlay.hint.text()
    assert overlay.run.checks[-1].key == "texts" and overlay.run.checks[-1].state == NOTE
    stored = app.service.instrument_history("TEST0001")
    assert stored[0].title == "Test über Bluetooth" and len(stored[0].checks) == 7


def test_the_log_opens_without_an_instrument_and_shows_the_runs(app, qtbot):
    from okeydocu.ui.instrument_log import InstrumentLogOverlay
    app.service.save_instrument_test("prime", "USB", run_checks(_Instrument(), date(2026, 5, 4)))
    log = InstrumentLogOverlay(app)
    qtbot.addWidget(log)
    assert log.instrument.currentData() == "TEST0001"
    assert log.tree.topLevelItemCount() == 1 and log.tree.topLevelItem(0).childCount() == 6
    assert log.tree.topLevelItem(0).text(1) == "✓ Test über USB"


def test_an_empty_log_says_why(app, qtbot):
    from okeydocu.l10n import tr
    from okeydocu.ui.instrument_log import EMPTY, InstrumentLogOverlay
    log = InstrumentLogOverlay(app)
    qtbot.addWidget(log)
    assert log.hint.text() == tr(EMPTY) and not log.copy_button.isEnabled()


class _SlowToConnect(_Instrument):
    """Hangs while connecting until the window cancels."""

    def __init__(self):
        super().__init__()
        import threading
        self.stop = threading.Event()

    def abort(self):
        self.stop.set()

    def open(self):
        self.stop.wait(5)
        raise DeviceError("abgebrochen")


def test_a_test_that_waits_can_be_cancelled_and_keeps_nothing(app, qtbot, monkeypatch):
    from okeydocu.ui.instrument_test import InstrumentTestOverlay
    monkeypatch.setattr(app.devices, "new_driver", lambda key, port="": _SlowToConnect())
    overlay = InstrumentTestOverlay(app, "prime", "bt:00:11:22:33:44:55", "PRIME (Bluetooth)")
    qtbot.addWidget(overlay)
    assert overlay.cancel_button.isEnabled() and not overlay.busy.isHidden()
    overlay.reject()
    qtbot.waitUntil(lambda: not overlay.worker.isRunning(), timeout=3000)
    qtbot.wait(20)
    assert overlay.run is None and not overlay.accepted
    assert app.service.instrument_history("TEST0001") == []
