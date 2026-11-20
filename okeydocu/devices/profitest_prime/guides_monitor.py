# OkeyDocu - okeydocu/devices/profitest_prime/guides_monitor.py
# The PROFITEST PRIME's guides for monitoring devices: insulation monitor, residual current monitor.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A monitor only raises an alarm, so the tester is the one who sees it respond: the instrument
makes the fault, runs a stop watch and is stopped by hand when the alarm comes. The tester then
rates the response with two softkeys, and only a rated result can be shared. The insulation
monitor gets a resistance between a line conductor and PE, the residual current monitor a
constant test current, after the touch voltage was measured as at an RCD."""

from __future__ import annotations

from ...l10n import N_
from ..guide import Action, Guide, Lead
from . import screens
from .guide_parts import L_LEAD, LIVE_PARTS, N_LEAD, PE_BAR, STORE, flow

ON = N_("Leave it switched on")
ALARM = (N_("Inform the operator"), N_("The alarm is raised: what it switches reacts too."))
RATE = Action((), N_("Rate the response with the softkeys ✓ and ✗: only a rated result can be"
                     " shared."))

IMD = Guide(
    "imd", N_("IMD response test"), 25, "imd", N_("IMD, conductors of the IT system"),
    (PE_BAR,
     Lead(*L_LEAD, "l1", N_("Place probe L (L1) on line conductor L1 of the IT system.")),
     Lead(*N_LEAD, "l2", N_("Place probe N (L3) on line conductor L2."))),
    LIVE_PARTS, "imd_type", ("imd_type", "alarm_value"), True,
    ((ON, N_("The monitor is tested on the live IT system.")), ALARM,
     (N_("Mind sensitive parts"), N_("A low test resistance means a high current: protect"
                                     " sensitive parts."))),
    "IMD",
    N_("Switches a resistance between a line conductor and PE, as an insulation fault would,"
       " and stops the time until the monitor raises its alarm. The resistance goes from"
       " 15 kΩ to 2,5 MΩ in steps."),
    settings=(Action((), N_("Sequence: with MAN the softkeys change the resistance, with AUTO it"
                            " changes by itself every 2 s, starting at RSTART."),
                     screens.IMD_SEQUENCE),
              Action((), N_("RSTART: the resistance the test begins with."), screens.IMD_START),
              Action((), N_("Conductor and range: the line conductor the resistance goes to,"
                            " and how far the monitor's own reading may lie from it."),
                     screens.IMD_PATH)),
    steps=(Action(("key-start",), N_("With the probes in place press ON/START: the resistance"
                                     " is switched in and the time runs.")),
           Action((), N_("With MAN change the resistance with the softkeys showing a rising and"
                         " a falling ramp; each change starts the time anew.")),
           Action(("key-idn",), N_("IΔN changes to the other line conductor.")),
           Action(("key-start",), N_("As soon as the monitor raises its alarm press ON/START"
                                     " again: the time stops.")),
           RATE, STORE),
    screen=screens.IMD, result_key=screens.RESULT, drawing_features=("alarm_value",),
    flow=flow())
RCM = Guide(
    "rcm_touch", N_("RCM response test"), 26, "rcm", N_("RCM, load side of its transformer"),
    (PE_BAR,
     Lead(*L_LEAD, "out_l", N_("Place probe L (L1) on a line conductor on the load side of the"
                               " transformer.")),
     Lead(*N_LEAD, "out_n", N_("Place probe N (L3) on N of the load side: a test with direct"
                               " current needs it."))),
    LIVE_PARTS, "rcm_type", ("rcm_type", "rated_residual_current"), True,
    ((ON, N_("The monitor and the circuit stay on.")), ALARM,
     (N_("RCD in the same circuit"), N_("The test current may trip it: secure the loads"
                                        " beforehand."))),
    "RCM",
    N_("Measures the touch voltage, then sends a constant test current: at half the rated"
       " residual current the monitor has to stay quiet for 10 s, at the full one it has to"
       " raise its alarm, and the time is stopped by hand."),
    settings=(Action((), N_("Monitor and test: rated residual current, waveform, type, rated"
                            " current and earthing system as the monitor states them; the"
                            " factor chooses the test, ½ × IΔN or 1 × IΔN."),
                     screens.RCM_TEST),
              Action((), N_("Limits: the highest touch voltage allowed."), screens.LIMITS)),
    steps=(Action(("key-start",), N_("Press ON/START: the touch voltage is measured, the"
                                     " monitor stays quiet.")),
           Action(("key-idn",), N_("Press IΔN: the test current flows. With ½ × IΔN no alarm"
                                   " may come within 10 s.")),
           Action(("key-idn",), N_("With 1 × IΔN press IΔN again as soon as the monitor raises"
                                   " its alarm: the time stops.")),
           RATE, STORE),
    screen=screens.RCM, result_key=screens.RESULT,
    drawing_features=("rated_residual_current",), flow=flow())
