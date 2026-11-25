# OkeyDocu - okeydocu/devices/profitest_prime/simulated.py
# A PROFITEST PRIME without hardware, for a test project to play with.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The instrument as far as the program sees it, without the instrument: its front panel, its
dial positions, its guides and its setting lists, with random readings. It serves a test
project to try the program with; a campaign measured with it says so in its report and cannot
be signed. The switch stands where the drawn dial was last turned to, or where the function
last measured has its position."""

from __future__ import annotations

from datetime import date, timedelta

from ...l10n import N_, tr
from ...model import DeviceIdentity
from ..base import DeviceError, FoundInstrument, SelectorPosition
from ..driver_info import DriverInfo
from ..simulator import SimulatedMeter
from . import panel
from .guides import GUIDES, guide_for
from .selector import selector_position
from .setting_lists import setting_list

KEY = "profitest-prime-simulated"
LABEL = N_("PROFITEST PRIME, simulated (no hardware)")
# Functions whose readings are drawn like those of another one.
LIKE = {"rlo_25a": "rlo", "riso_ramp": "riso", "i_ramp": "rcd_time", "zloop_dc": "zloop",
        "zloop_rlo": "zloop", "zloop_half": "zloop"}


class SimulatedPrime(SimulatedMeter):
    simulated_functions = tuple(
        function for function in GUIDES
        if LIKE.get(function, function) in SimulatedMeter.simulated_functions)

    def __init__(self, **options):
        super().__init__(**options)
        self.position: int | None = None  # where the switch stands, as the instrument counts

    def identify(self) -> DeviceIdentity:
        due = date.today() + timedelta(days=200)
        return DeviceIdentity("Simulator", tr("PROFITEST PRIME, simulated"), "SIM-0002", "1.0",
                              calibrated_on=due - timedelta(days=365), recalibration_due=due)

    def turn(self, value: int) -> None:
        """The switch turned by hand, on the drawn dial."""
        self.position = value

    def read_selector(self) -> SelectorPosition:
        if self.position is None:
            raise DeviceError(tr("The rotary switch has not been moved yet."))
        return selector_position(self.position)

    def _drawn(self, function: str):
        return super()._drawn(LIKE.get(function, function))

    def simulate_measurement(self, function: str, at=None):
        self.position = guide_for(function).selector if function in GUIDES else self.position
        return super().simulate_measurement(function, at)


def find() -> list[FoundInstrument]:
    return [FoundInstrument(KEY, tr(LABEL))]


DRIVER = DriverInfo(KEY, LABEL, SimulatedPrime, find=find, panel=panel.DRAWING, guide=guide_for,
                    guided=tuple(GUIDES), setting_list=setting_list, simulated=True)
