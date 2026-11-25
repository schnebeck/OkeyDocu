# OkeyDocu - tools/readme_images/shot_guide.py
# Pictures of the guided measurement: rotary switch and test leads.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes guide-dial and guide-leads, and both once more at three times the size as sources
for the stand-in photos."""
import os
import time

from okeydocu.devices.guide import CONNECT, SELECT
from okeydocu.devices.profitest_prime.selector import selector_position
from okeydocu.ui.measuring_window import MeasuringWindow

import demo
from staging import LANG, breeze, save, save_sharp

REPORTED = int(os.environ.get("SHOT_DIAL", "17"))  # where the instrument says its switch stands


def settle(qtbot, seconds: float) -> None:
    """Lets the animations of a station run out."""
    end = time.time() + seconds
    while time.time() < end:
        qtbot.wait(40)


def test_guide(app, qtbot):
    breeze()
    ids = demo.plant(app, LANG)
    campaign = demo.open_campaign(app, ids, demo.WORDS[LANG]["now"], LANG)
    window = MeasuringWindow(app, campaign, demo.DRIVER, "rcd_time", ids["rcd"])
    qtbot.addWidget(window)
    window.resize(1440, 960)
    window.show()
    qtbot.wait(300)
    window.go_to(SELECT)
    window.show_selector(selector_position(REPORTED))
    settle(qtbot, 1.6)
    window.poll.stop()
    save(window, f"guide-dial-{LANG}")
    save_sharp(window, f"sharp-dial-{LANG}")
    window.show_selector(selector_position(window.guide.selector))
    settle(qtbot, 1.0)
    window.go_to(CONNECT)
    settle(qtbot, 3.0)
    save(window, f"guide-leads-{LANG}")
    save_sharp(window, f"sharp-leads-{LANG}")
