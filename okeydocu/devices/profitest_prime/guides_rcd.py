# OkeyDocu - okeydocu/devices/profitest_prime/guides_rcd.py
# The PROFITEST PRIME's guides for RCDs: tripping time, tripping current, both in one run.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""All three run alike: ON/START measures the touch voltage with a current too small to trip,
then IΔN sends the test current that trips the RCD. They differ in the dial position, in the
test current and in what is measured at the trip. The position for both in one run serves the
other two as well, with the RCD data in another softkey row."""

from __future__ import annotations

from ...l10n import N_
from ..guide import Action, Guide, Lead
from . import screens
from .guide_parts import L_LEAD, LIMITS, N_LEAD, PE_BAR, RCD_SIDE, STORE, flow

FEATURES = ("rcd_type", "rated_residual_current", "rated_current", "number_of_poles",
            "n_terminal")
SECURE = (N_("Secure the loads"), N_("Save data, stop running machines."))
BEFORE = (
    (N_("Inform the operator"), N_("The test switches the circuit off.")),
    SECURE,
    (N_("Leave it switched on"), N_("The RCD and the circuit stay on.")),
)
TO_L = Lead(*L_LEAD, "out_l", N_("Place probe L (L1) on the outgoing line conductor terminal of"
                                 " the RCD, usually an upper one."))
LEADS = (PE_BAR, TO_L,
         Lead(*N_LEAD, "out_n", N_("Place probe N (L3) on the outgoing N terminal of the RCD.")))
CAUTION = N_("The test switches the circuit off. Secure the loads beforehand.")
DATA = Action((), N_("RCD: rated residual current IΔN, type and rated current IN, as the RCD"
                     " states them."), screens.RCD)
TOUCH = Action(("key-start",), N_("Press ON/START: the touch voltage is measured, the RCD does"
                                  " not trip yet."))
BOTH_VIEW = ((19, screens.RCD_BOTH),)


def rcd_guide(function: str, title: str, selector: int, label: str, note: str, own: tuple,
              trip: str, screen, **more) -> Guide:
    """`own` are the settings between RCD data and limits, `trip` what the IΔN key does."""
    return Guide(
        function, title, selector, *RCD_SIDE, LEADS, CAUTION, "rcd_type", FEATURES, True,
        BEFORE, label, note,
        settings=(DATA, *own, Action((), LIMITS, screens.LIMITS)),
        steps=(TOUCH, Action(("key-idn",), trip), STORE),
        screen=screen, result_key=screens.RESULT, flow=flow(), **more)


RCD_TIME = rcd_guide(
    "rcd_time", N_("RCD tripping test IΔN"), 18, "IΔN",
    N_("Measures the touch voltage and the tripping time at the rated residual current."),
    (Action((), N_("Test current: waveform, 1 × IΔN and the earthing system."),
            screens.TEST_CURRENT),),
    N_("Press IΔN: the RCD trips and the tripping time is measured."),
    screens.RCD_TIME, screens=BOTH_VIEW, results=("rcd_touch",))
RCD_CURRENT = rcd_guide(
    "rcd_current", N_("RCD tripping current IF"), 17, "IF◢",
    N_("Measures the touch voltage and the current at which the RCD trips, with a rising test"
       " current."),
    (Action((), N_("Waveform of the test current and the earthing system."),
            screens.EARTHING),),
    N_("Press IΔN: the test current rises until the RCD trips; the tripping current is"
       " measured."),
    screens.RCD_RAMP, screens=BOTH_VIEW, results=("rcd_ramp_touch",))
RCD_BOTH = rcd_guide(
    "i_ramp", N_("RCD tripping current and time"), 19, "IF◢+IΔN",
    N_("Measures touch voltage, tripping current and tripping time in one run, with a rising"
       " test current."),
    (),
    N_("Press IΔN: the test current rises until the RCD trips; tripping current and tripping"
       " time are measured."),
    screens.RCD_BOTH, results=("rcd_current", "rcd_time", "rcd_touch", "rcd_ramp_touch"))
