# EasyMeasurement - tests/test_device_texts.py
# The instrument's words for its codes: read on setting it up, kept, and used to show settings.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from dataclasses import asdict
from datetime import datetime

import pytest

from easymeasurement.devices import Capability, DeviceBlocked, DeviceTexts
from easymeasurement.devices.profitest_prime.texts import parse_texts
from easymeasurement.model import DeviceIdentity, Parameter, Verdict
from easymeasurement.ui.instrument_prepare import InstrumentPrepareOverlay, texts_needed

# Invented codes and words: the instrument's own texts stay out of the project.
TEXTS = {"de-DE": {"TS9001": "Prüfmodus", "TS9002": "Langsam"},
         "en-GB": {"TS9001": "Test mode", "TS9002": "Slow"}}
XML = b"""<?xml version="1.0"?><sl:LANGUAGES xmlns:sl="urn:example"><sl:TRANSLATIONS>
<sl:MoFile Culture="de-DE" Version="1.2.3"><sl:TRANSLATION Key="TS9001">Pr\xc3\xbcfmodus</sl:TRANSLATION>
<sl:TRANSLATION Key="TS9002"> Langsam </sl:TRANSLATION></sl:MoFile>
<sl:MoFile Culture="en-GB" Version="1.2.3"><sl:TRANSLATION Key="TS9001">Test mode</sl:TRANSLATION>
<sl:TRANSLATION Key="TS9002">Slow</sl:TRANSLATION></sl:MoFile></sl:TRANSLATIONS></sl:LANGUAGES>"""


def test_the_translation_file_becomes_texts_per_language():
    texts = parse_texts(XML)
    assert texts.version == "1.2.3" and texts.texts == TEXTS


def test_kept_texts_replace_older_ones_and_name_their_firmware(app):
    app.db.save_device_texts("prime", "01.00.00", "1", {"de-DE": {"TS9999": "alt"}})
    app.db.save_device_texts("prime", "02.00.00", "2", TEXTS)
    assert app.db.device_text_firmware("prime") == "02.00.00"
    assert app.db.device_texts("prime", "de-DE") == TEXTS["de-DE"]
    assert app.db.device_texts("prime", "en-GB")["TS9002"] == "Slow"
    assert app.db.device_texts("another", "de-DE") == {}


def _words(app):
    from easymeasurement.devices.naming import InstrumentWords, SettingWords
    from easymeasurement.devices.profitest_prime import mapping
    app.db.save_device_texts("prime", "02.00.00", "2", TEXTS)
    return SettingWords(app.db, [InstrumentWords("prime", mapping.is_code, mapping.culture)])


def test_a_setting_reads_as_words_where_they_are_known(app):
    words = _words(app)
    assert words.say("TS9001", "TS9002") == ("Prüfmodus", "Langsam", True)
    assert words.say("TS9001", "500 V") == ("Prüfmodus", "500 V", True)
    assert words.say("TS9003", "TS9002") == ("TS9003", "Langsam", False)
    assert words.say("conductor", "L1-PE") == ("Leiter", "L1-PE", True)  # the vocabulary's


def test_the_instrument_speaks_the_language_of_the_program(app):
    from easymeasurement.l10n import speaking
    with speaking("en"):
        assert _words(app).say("TS9001", "TS9002") == ("Test mode", "Slow", True)


class _Instrument:
    """Answers like an instrument with texts; counts how often they were read."""

    capabilities = Capability.TEXTS

    def __init__(self, firmware="02.00.00", blocked=False):
        self.firmware, self.blocked, self.reads = firmware, blocked, 0

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        pass

    def identify(self):
        return DeviceIdentity("Hersteller", "Modell", "TEST0001", self.firmware)

    def read_texts(self):
        if self.blocked:
            raise DeviceBlocked("Daten gerade nicht frei.")
        self.reads += 1
        return DeviceTexts("2", TEXTS)


def _prepare(app, qtbot, monkeypatch, instrument):
    monkeypatch.setattr(app.devices, "new_driver", lambda key, port="": instrument)
    overlay = InstrumentPrepareOverlay(app, "prime", "bt:00:11:22:33:44:55")
    qtbot.addWidget(overlay)
    qtbot.waitUntil(lambda: not overlay.worker.isRunning(), timeout=3000)
    qtbot.wait(20)  # the worker's signals reach the window
    return overlay


def test_setting_up_brings_the_texts_over_once_per_firmware(app, qtbot, monkeypatch):
    instrument = _Instrument()
    overlay = _prepare(app, qtbot, monkeypatch, instrument)
    assert overlay.done and instrument.reads == 1
    assert app.db.device_text_firmware("prime") == "02.00.00"
    assert overlay.states == {"identify": "done", "texts": "done"}
    again = _prepare(app, qtbot, monkeypatch, instrument)
    assert again.states["texts"] == "skipped" and instrument.reads == 1


def test_an_update_of_the_firmware_asks_for_the_texts_again(app):
    app.db.save_device_texts("prime", "02.00.00", "2", TEXTS)
    assert not texts_needed(app, "prime", "02.00.00", Capability.TEXTS)
    assert texts_needed(app, "prime", "02.01.00", Capability.TEXTS)
    assert not texts_needed(app, "prime", "02.01.00", Capability.NONE)


def test_a_blocked_instrument_asks_for_setup_and_can_be_tried_again(app, qtbot, monkeypatch):
    overlay = _prepare(app, qtbot, monkeypatch, _Instrument(blocked=True))
    assert not overlay.done and "Setup" in overlay.hint.text()
    assert overlay.ok_button.text() == "Erneut versuchen" and overlay.cancel_button.isEnabled()
    assert app.db.device_text_firmware("prime") is None


def test_a_changed_setting_is_judged_in_words_on_both_sides(app):
    """A push sends codes, an import brings German text: they must not look different."""
    from easymeasurement.campaign.plan import PlanStep
    from easymeasurement.devices.profitest_prime.discovery import DRIVER_KEY
    app.db.save_device_texts(DRIVER_KEY, "02.00.00", "2", TEXTS)
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    measured = app.service.add_measurement(
        campaign, "rlo", [], datetime(2026, 5, 4, 9, 0), Verdict.PASSED)
    app.db.execute("UPDATE measurements SET parameters_json=? WHERE id=?",
                   json.dumps([asdict(Parameter("TS9001", "TS9002"))]), measured)  # as a push
    same = PlanStep(key="r1", title="RLO", parameters=(("TS9001", "Langsam"),))
    other = PlanStep(key="r2", title="RLO", parameters=(("TS9001", "Schnell"),))
    assert app.service.deviations(same, measured) == []
    assert app.service.deviations(other, measured) == ["Prüfmodus: Langsam statt Schnell"]


@pytest.mark.parametrize("command", ["DATABASEXML:GET:TRANSLATIONFILE"])
def test_reading_the_texts_is_an_approved_read(command):
    from easymeasurement.devices.profitest_prime.transport import READ_ONLY_COMMANDS
    assert command in READ_ONLY_COMMANDS


def test_the_instruments_dialog_sets_up_the_chosen_instrument(app, qtbot, monkeypatch):
    from easymeasurement.devices import FoundInstrument
    from easymeasurement.ui import settings_dialog
    found = FoundInstrument("profitest-prime", "PROFITEST PRIME (USB)", "/dev/ttyACM0")
    monkeypatch.setattr(settings_dialog, "find_instruments", lambda: [found])
    opened = []
    monkeypatch.setattr(settings_dialog.InstrumentPrepareOverlay, "__init__",
                        lambda self, app, key, port, parent=None: opened.append((key, port)))
    monkeypatch.setattr(settings_dialog.InstrumentPrepareOverlay, "exec", lambda self: 1)
    dialog = settings_dialog.SettingsOverlay(None, app)
    qtbot.addWidget(dialog)
    assert dialog.prepare_button.isEnabled()
    dialog.prepare_button.click()
    assert opened == [("profitest-prime", "/dev/ttyACM0")]


def test_pairing_over_bluetooth_goes_straight_on_to_setting_up(app, qtbot, monkeypatch):
    from easymeasurement.ui import settings_dialog
    opened = []
    monkeypatch.setattr(settings_dialog.InstrumentPrepareOverlay, "__init__",
                        lambda self, app, key, port, parent=None: opened.append((key, port)))
    monkeypatch.setattr(settings_dialog.InstrumentPrepareOverlay, "exec", lambda self: 1)

    def paired(self):
        self.address = "00:11:22:33:44:55"
        return 1

    monkeypatch.setattr(settings_dialog.InstrumentSetupOverlay, "exec", paired)
    dialog = settings_dialog.SettingsOverlay(None, app)
    qtbot.addWidget(dialog)
    dialog.set_up_button.click()
    assert opened == [("profitest-prime", "bt:00:11:22:33:44:55")]
