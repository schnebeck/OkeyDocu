# OkeyDocu - okeydocu/devices/profitest_prime/info.py
# The PROFITEST PRIME as the application sees it: name, finding, words, pairing, hints.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Callable

from ...l10n import N_
from ..driver_info import DriverInfo, Pairing
from ..naming import InstrumentWords
from . import mapping, pairing, panel
from .discovery import DRIVER_KEY, LABEL, find_instruments
from .driver import ProfitestPrimeDriver
from .guides import GUIDES, guide_for

PAIRING_BUTTON = N_("Set up {instrument} via Bluetooth …")
PAIRING_STEPS = N_(
    "<ol>"
    "<li>Unplug the USB cable.</li>"
    "<li>Turn the rotary switch to <b>Setup</b>.</li>"
    "<li>In the Bluetooth menu, set Bluetooth to <b>on</b> and <b>visible</b>.</li>"
    "<li>Click <b>Set up</b> here and confirm a request on the instrument.</li>"
    "</ol>"
    "This is needed only once. After that the instrument is in the list and only gets chosen."
)
PREPARING = N_("The instrument is being prepared for this program. The first time and after a"
               " firmware update this takes about a minute. Please leave the rotary switch at"
               " <b>Setup</b> and do not disconnect the instrument.")


def _pair(pin: str, on_progress: Callable[[str], None]) -> str:
    return f"bt:{pairing.pair_instrument(pin, on_progress)}"


DRIVER = DriverInfo(
    key=DRIVER_KEY,
    label=LABEL,
    factory=ProfitestPrimeDriver,
    find=find_instruments,
    words=InstrumentWords(DRIVER_KEY, mapping.is_code, mapping.culture),
    instructions=mapping.instruction_folder(),
    pairing=Pairing(PAIRING_BUTTON, PAIRING_STEPS, _pair, pairing.DEFAULT_PIN),
    panel=panel.DRAWING,
    guide=guide_for,
    guided=tuple(GUIDES),
    preparing=PREPARING,
)
