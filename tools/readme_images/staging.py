# OkeyDocu - tools/readme_images/staging.py
# What the picture scripts share: language, a stand-in instrument, saving.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The scripts run under pytest with the fixtures of the test suite, so each starts from an
empty database in a folder of its own. `SHOT_LANG` chooses the language of the program,
`README_OUT` the folder the pictures are written to."""
import os
import sys
from dataclasses import replace

sys.path.insert(0, os.path.dirname(__file__))
LANG = os.environ.get("SHOT_LANG", "en")
from okeydocu.l10n import set_language  # noqa: E402

set_language(LANG)  # before any window is made

from PySide6.QtGui import QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from okeydocu.devices import registry  # noqa: E402
from okeydocu.devices.simulator import SimulatedMeter  # noqa: E402

import demo  # noqa: E402

OUT = os.path.join(os.environ.get("README_OUT", os.path.join(os.path.dirname(__file__), "out")),
                   "")
os.makedirs(OUT, exist_ok=True)


class StandIn(SimulatedMeter):
    """Answers like an instrument that is connected and sends nothing by itself."""

    def identify(self):
        return demo.IDENTITY


def breeze() -> None:
    """The pictures show the desktop style the program is made for."""
    assert QApplication.style().objectName() == "breeze", "run with QT_STYLE_OVERRIDE=Breeze"


def connected_prime(monkeypatch) -> None:
    info = registry.driver_info(demo.DRIVER)
    monkeypatch.setitem(registry._DRIVERS, demo.DRIVER,
                        replace(info, factory=lambda **options: StandIn()))


def quiet(page) -> None:
    """The stand-in is a simulator; what triggers it has no place in a picture."""
    page.free.simulate_function.hide()
    page.free.simulate_button.hide()


def go_live(page, campaign, qtbot) -> None:
    page.enter(campaign)
    qtbot.wait(300)
    quiet(page)


def save(widget, name, rect=None) -> str:
    path = f"{OUT}{name}.png"
    (widget.grab(rect) if rect is not None else widget.grab()).save(path)
    return path


def save_sharp(widget, name, factor=3) -> None:
    """The widget drawn at a multiple of its size, as a source for stand-in photos."""
    pixmap = QPixmap(widget.size() * factor)
    pixmap.setDevicePixelRatio(factor)
    widget.render(pixmap)
    pixmap.save(f"{OUT}{name}.png")
