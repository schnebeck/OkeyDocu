# OkeyDocu - okeydocu/devices/profitest_prime/guides_resistance.py
# The PROFITEST PRIME's guides measured dead at the machine's plug: protective conductor and
# insulation.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The protective conductor is measured from the PE contact of the pulled plug to the housing,
with 200 mA from the battery or with 25 A from the mains. The insulation is measured from a
line conductor contact to the PE contact, with a constant test voltage or with one that rises
until something responds; its probes stay on until the test point is discharged."""

from __future__ import annotations

from dataclasses import replace

from ...l10n import N_
from ..guide import Action, Guide, Lead
from . import screens
from .guide_parts import (
    CONDUCTORS,
    L_LEAD,
    LIMITS,
    MAINS,
    NEXT_PAIR,
    PATH,
    PE_LEAD,
    PLUG_OFF,
    START,
    STORE,
    flow,
)

OFFSET = Action((), N_("With an extension lead: compensate it first (ROFFSET)."), screens.OFFSET)
PROTECTIVE_CONDUCTOR = Guide(
    "rlo", N_("Protective conductor resistance"), 13, "cee_plug",
    N_("CEE plug and housing of the machine"),
    (Lead(*L_LEAD, "pe_pin", N_("Place probe L (L1) on the PE contact of the CEE plug.")),
     Lead(*PE_LEAD, "body", N_("Place probe PE (L2) on a bare metal spot of the housing."))),
    N_("Measure only dead: the plug is pulled."),
    element_features=CONDUCTORS, live=False,
    preparation=((PLUG_OFF, N_("The protective conductor is measured without voltage.")),
                 (N_("Find a bare metal spot"), N_("Paint and rust falsify the result."))),
    selector_label="RLO",
    selector_note=N_("Measures the resistance of the protective conductor with 200 mA."),
    settings=(Action((), N_("Polarity: both directions, the larger value counts."),
                     screens.SIGNAL),
              Action((), LIMITS, screens.LIMITS), OFFSET),
    steps=(Action(("key-start",), N_("Press ON/START and hold the probes until the result"
                                     " stands.")), STORE),
    screen=screens.RLO, result_key=screens.RESULT, drawing_features=("rated_current",),
    flow=flow())
HIGH_CURRENT = replace(
    PROTECTIVE_CONDUCTOR, function="rlo_25a", selector=14, selector_label="RLO 25A",
    title=N_("Protective conductor resistance with 25 A"),
    selector_note=N_("Measures the protective conductor with 25 A from the mains: for large"
                     " cross-sections and short leads."),
    settings=(Action((), N_("Limits: by hand, or with the key 60204-1 from the cross-section"
                            " of the line conductors and the protective device in front."),
                     screens.LIMITS), OFFSET),
    screen=screens.RLO_25A, flow=flow(MAINS))

CHARGED = N_("The probes carry the test voltage: do not touch them, and leave them on until the"
             " voltage shown has fallen below 10 V.")
DISCHARGE = Action((), N_("Leave the probes on until the voltage shown has fallen below 10 V."))
INSULATION = Guide(
    "riso", N_("Insulation resistance"), 15, "cee_plug", N_("CEE plug of the machine, pulled"),
    (Lead(*PE_LEAD, "pe_pin", N_("Place probe PE (L2) on the PE contact of the CEE plug.")),
     Lead(*L_LEAD, "l_pin", N_("Place probe L (L1) on the contact of line conductor L1."))),
    CHARGED, element_features=CONDUCTORS, live=False,
    preparation=((PLUG_OFF, N_("The insulation is measured without voltage.")),
                 (N_("Switch the machine's main switch on"),
                  N_("So the circuits behind it are measured too.")),
                 (N_("Mind sensitive parts"),
                  N_("Disconnect what the test voltage would damage, or lower it."))),
    selector_label="RISO",
    selector_note=N_("Measures the insulation resistance with a constant test voltage."),
    settings=(Action((), N_("Test voltage: 500 V is usual; lower where parts would not stand"
                            " it."), screens.TEST_VOLTAGE),
              Action((), LIMITS, screens.LIMITS), Action((), PATH, screens.RISO_PATH)),
    steps=(START, DISCHARGE, STORE, NEXT_PAIR),
    screen=screens.RISO, result_key=screens.RESULT, drawing_features=("rated_current",),
    every_path=True, flow=flow())
RISING = replace(
    INSULATION, function="riso_ramp", selector=16, selector_label="RISO◢",
    title=N_("Insulation with rising voltage"),
    selector_note=N_("Raises the test voltage until a surge protective device or a weak spot"
                     " of the insulation responds, and shows that voltage."),
    settings=(Action((), N_("Current limit ILIM: the measurement stops when this current"
                            " flows."), screens.CURRENT_LIMIT),
              Action((), N_("Test voltage: the highest voltage the ramp reaches."),
                     screens.TEST_VOLTAGE),
              Action((), N_("Limits: the range the voltage of the response has to lie in."),
                     screens.LIMITS),
              Action((), PATH, screens.RISO_PATH)),
    steps=(Action(("key-start",), N_(
        "With the probes in place press ON/START briefly: the voltage rises until something"
        " responds, the test voltage is reached or the current limit flows.")),
        DISCHARGE, STORE, NEXT_PAIR),
    screen=screens.RISO_RAMP)
