# OkeyDocu - tools/readme_images/shot_instruments.py
# Pictures of several instruments in one campaign and of the climate sensor.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes instruments-head (the campaign head naming the PROFITEST PRIME and a climate sensor
beside it), sensor-enrol (the enrolment card with two sensors in reach, one enrolled) and
sensor-settle (the guided measurement of the ambient conditions while the sensor settles).
The sensors and their addresses are invented."""
import time

from PySide6.QtCore import QRect

from okeydocu.devices import FoundInstrument, registry
from okeydocu.devices.climate.known import KnownSensor, remember
from okeydocu.devices.climate.simulated import SimulatedClimate
from okeydocu.devices.guide import SETTLE
from okeydocu.model import DeviceIdentity
from okeydocu.ui.measuring_window import MeasuringWindow
from okeydocu.ui.sensor_enrolment import SensorEnrolmentOverlay

import demo
from staging import LANG, breeze, connected_prime, go_live, quiet, save

HALL, STORE = "00:00:5E:00:53:01", "00:00:5E:00:53:02"  # documentation addresses (RFC 7042)
SENSOR = DeviceIdentity("Example", "LYWSD03MMC", HALL, "pvvx 4.9", name="Climate-01")


def test_instruments(window, app, qtbot, monkeypatch):
    breeze()
    connected_prime(monkeypatch)
    ids = demo.plant(app, LANG)
    campaign = demo.open_campaign(app, ids, demo.WORDS[LANG]["now"], LANG)
    app.service.book(campaign, "climate", SENSOR, beside=True)
    page = window.campaign
    window.resize(1560, 900)
    go_live(page, campaign, qtbot)
    page.show_campaign(campaign)
    quiet(page)
    starter = page.free.starter
    starter.choice.setCurrentIndex(starter.choice.findData("ambient"))
    qtbot.wait(400)
    corner = page.header.mapTo(window, page.header.rect().topLeft())
    right = page.header.mapTo(window, page.header.rect().topRight()).x()
    bottom = page.free.mapTo(window, page.free.rect().bottomLeft()).y()
    save(window, f"instruments-head-{LANG}",
         QRect(0, corner.y() - 8, right + 8, bottom - corner.y() + 16))

    remember(KnownSensor(HALL, "Climate-01", "bthome"))
    card = SensorEnrolmentOverlay([registry.driver_info("climate")], window)
    card._listed([FoundInstrument("climate", "Climate-01  BTHome v2  21.4 \u00b0C", HALL,
                                  "Climate-01"),
                  FoundInstrument("climate", "Climate-02  pvvx  23.9 \u00b0C", STORE,
                                  "Climate-02")])
    card.sensors.setCurrentRow(1)
    card._open()
    qtbot.wait(400)
    box = card.card.geometry()
    save(window, f"sensor-enrol-{LANG}", box.adjusted(-24, -24, 24, 24))
    card.reject()

    sensor = SimulatedClimate("sim-1")
    window_ = MeasuringWindow(app, campaign, "climate-simulator", "ambient", ids["machine"],
                              sensor=sensor)
    qtbot.addWidget(window_)
    window_.resize(1440, 960)
    window_.show()
    window_.go_to(SETTLE)
    end = time.time() + 6.0  # the sensor out of a warm pocket, still settling
    while time.time() < end:
        qtbot.wait(200)
    window_._sensor_tick()
    save(window_, f"sensor-settle-{LANG}", QRect(0, 0, 1440, 520))  # the rest is empty
