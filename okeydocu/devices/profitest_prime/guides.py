# OkeyDocu - okeydocu/devices/profitest_prime/guides.py
# The PROFITEST PRIME's side of guided first measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""One guide per measuring function, by the function a reading of it carries. The guides
themselves stand with their kind: voltage, RCD, measurements at the pulled plug, loop
impedance, residual voltage, monitoring devices, small currents, voltage drop. A softkey is named by the row of the display that shows its setting, so it
is pointed at where the view of the dial position has it."""

from __future__ import annotations

from ..guide import Guide
from .guide_parts import MAINS, flow
from .guides_current import CLAMP_CURRENT, TOUCH_CURRENT
from .guides_drop import VOLTAGE_DROP
from .guides_loop import LOOP, LOOP_COMBINED, LOOP_DC, LOOP_REDUCED
from .guides_monitor import IMD, RCM
from .guides_rcd import RCD_BOTH, RCD_CURRENT, RCD_TIME
from .guides_residual import RESIDUAL
from .guides_resistance import HIGH_CURRENT, INSULATION, PROTECTIVE_CONDUCTOR, RISING
from .guides_voltage import VOLTAGE

__all__ = ["GUIDES", "MAINS", "flow", "guide_for"]

GUIDES = {guide.function: guide for guide in (
    VOLTAGE, PROTECTIVE_CONDUCTOR, HIGH_CURRENT, INSULATION, RISING, RCD_TIME, RCD_CURRENT,
    RCD_BOTH, LOOP, LOOP_DC, LOOP_COMBINED, LOOP_REDUCED, RESIDUAL, IMD, RCM, TOUCH_CURRENT,
    CLAMP_CURRENT, VOLTAGE_DROP)}


def guide_for(function: str) -> Guide | None:
    return GUIDES.get(function)
