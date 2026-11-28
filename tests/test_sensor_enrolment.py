# OkeyDocu - tests/test_sensor_enrolment.py
# Enrolling a sensor, giving up on it, and dropping it again from the settings.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The radio is stood in for by an enrolment whose steps wait for the test to let them go."""

import threading
from dataclasses import replace

from okeydocu.devices import FoundInstrument, registry
from okeydocu.devices.climate.info import enrol
from okeydocu.devices.climate.known import known_sensors
from okeydocu.l10n import tr
from okeydocu.ui import settings_dialog
from okeydocu.ui.sensor_enrolment import SensorEnrolmentOverlay

ADDRESS = "00:11:22:33:44:55"  # invented
FOUND = FoundInstrument("climate", "Box 3  BTHome v2", ADDRESS, "Box 3")


class Sensor:
    """Stands in for the driver: tells who it is, takes a name."""

    def __init__(self, port):
        self.port = port

    def identify(self):
        from okeydocu.model import DeviceIdentity
        return DeviceIdentity("Example", "T1", self.port, "1.0", name="Box 3")

    def rename(self, name):
        pass


def enrolment(release: threading.Event):
    info = registry.driver_info("climate")

    def slow_enrol(port, name, given_up):
        release.wait(5)
        return enrol(port, name, given_up)
    return replace(info.enrolment, scan=lambda seconds, heard, stopped: [FOUND], enrol=slow_enrol)


def test_an_enrolment_given_up_keeps_nothing_and_the_card_closes_at_once(window, qtbot,
                                                                          monkeypatch):
    monkeypatch.setattr("okeydocu.devices.climate.info.ClimateSensor", Sensor)
    release = threading.Event()
    card = SensorEnrolmentOverlay(enrolment(release), window)
    card._listed([FOUND])
    card.sensors.setCurrentRow(0)
    card.name.setText("Box 7")
    card.accept()
    step = card.step
    card.reject()  # leaves while the sensor is still being enrolled
    assert card.given_up and not card.accepted
    release.set()
    qtbot.waitUntil(lambda: not step.isRunning(), timeout=5000)
    assert known_sensors() == []


def test_an_enrolled_sensor_is_listed_in_the_settings_and_dropped_there(window, qtbot,
                                                                         monkeypatch):
    monkeypatch.setattr("okeydocu.devices.climate.info.ClimateSensor", Sensor)
    assert enrol(ADDRESS, "Box 7").label.endswith("Box 7")
    monkeypatch.setattr(settings_dialog, "find_instruments", registry.find_instruments)
    card = settings_dialog.SettingsOverlay(window, window.app)
    names = [card.instruments.item(row).text() for row in range(card.instruments.count())]
    assert any(name.endswith("Box 7") for name in names)
    card.instruments.setCurrentRow(names.index(next(n for n in names if n.endswith("Box 7"))))
    assert card.forget_button.isVisibleTo(card) and not card.prepare_button.isEnabled()
    card.forget_button.click()
    assert known_sensors() == []


def test_a_sensor_chosen_offers_its_own_name_and_keeps_it_without_another(window, monkeypatch):
    monkeypatch.setattr("okeydocu.devices.climate.info.ClimateSensor", Sensor)
    card = SensorEnrolmentOverlay(registry.driver_info("climate").enrolment, window)
    card._listed([FOUND])
    assert card._chosen() is None and not card.enrol_button.isEnabled()  # nothing chosen
    card.sensors.setCurrentRow(0)
    assert card.name.text() == "Box 3" and card.enrol_button.isEnabled()
    enrol(ADDRESS, "")
    assert [sensor.name for sensor in known_sensors()] == ["Box 3"]


def test_an_enrolled_sensor_is_marked_and_its_button_unenrols_it(window, monkeypatch):
    monkeypatch.setattr("okeydocu.devices.climate.info.ClimateSensor", Sensor)
    card = SensorEnrolmentOverlay(registry.driver_info("climate").enrolment, window)
    card._listed([FOUND])
    card.sensors.setCurrentRow(0)
    assert card.enrol_button.text() == tr("Enrol")
    marked_before = card.sensors.item(0).icon().pixmap(12).toImage().pixelColor(6, 6).alpha()
    card._kept(enrol(ADDRESS, "Box 3"))
    assert not card.accepted  # the card stays open
    assert card.enrol_button.text() == tr("Unenrol")
    assert card.sensors.item(0).icon().pixmap(12).toImage().pixelColor(6, 6).alpha() > marked_before
    assert card.show_button.isEnabled()  # identifying stays open to every sensor
    card.accept()
    assert known_sensors() == [] and card.enrol_button.text() == tr("Enrol")


def test_the_list_fills_while_the_search_runs(window, qtbot):
    release = threading.Event()

    def scan(seconds, heard, stopped):
        heard(FOUND)
        for _ in range(100):  # until released or stopped, as the radio would
            if release.is_set() or stopped():
                break
            release.wait(0.05)
        return [FOUND]
    card = SensorEnrolmentOverlay(replace(registry.driver_info("climate").enrolment, scan=scan),
                                  window)
    card.search()
    qtbot.waitUntil(lambda: card.sensors.count() == 1, timeout=3000)
    assert card._busy()  # still listening
    release.set()
    qtbot.waitUntil(lambda: not card._busy(), timeout=3000)
    assert card.sensors.count() == 1


def test_a_sensor_listed_is_usable_at_once_and_ends_the_search(window, qtbot, monkeypatch):
    monkeypatch.setattr("okeydocu.devices.climate.info.ClimateSensor", Sensor)
    shown = []

    def scan(seconds, heard, stopped):
        heard(FOUND)
        for _ in range(200):
            if stopped():
                break
            threading.Event().wait(0.05)
        return [FOUND]
    enrolment = replace(registry.driver_info("climate").enrolment, scan=scan,
                        point_out=lambda port: shown.append(port) or 123)
    card = SensorEnrolmentOverlay(enrolment, window)
    card.search()
    qtbot.waitUntil(lambda: card.sensors.count() == 1, timeout=3000)
    card.sensors.setCurrentRow(0)
    assert card.show_button.isEnabled() and card.enrol_button.isEnabled()
    card.show_button.click()
    qtbot.waitUntil(lambda: shown == [ADDRESS], timeout=3000)
    qtbot.waitUntil(lambda: not card._busy(), timeout=3000)
    assert "123" in card.status.text()


def test_the_kinds_to_add_are_one_searchable_choice(window, monkeypatch):
    opened = []
    monkeypatch.setattr(settings_dialog.SettingsOverlay, "_enrol",
                        lambda self, info: opened.append(info.key))
    card = settings_dialog.SettingsOverlay(window, window.app)
    completer = card.adding.kinds.completer()
    completer.setCompletionPrefix("lima")  # any part of a name finds it
    assert completer.completionCount() == 1
    assert not card.adding.add_button.isEnabled()  # nothing chosen yet
    card.adding.choose("climate")
    card.adding.add_button.click()
    assert opened == ["climate"]
