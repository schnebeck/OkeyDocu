# OkeyDocu - okeydocu/devices/profitest_prime/guides_voltage.py
# The PROFITEST PRIME's guides for the voltage: single voltages and the three line voltages.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The voltage is measured as soon as the probes are on, without ON/START. The view U measures
between the probes L and PE only. The guide follows the line conductors the element states:
with three, the view U3~ measures between L1, L2 and L3 first, then the view U takes the
single voltages."""

from __future__ import annotations

from dataclasses import replace

from ...l10n import N_
from ..guide import (
    CONFIGURE,
    CONNECT,
    MEASURE,
    PLACE,
    PREPARE,
    SELECT,
    Action,
    Guide,
    Lead,
    Station,
    Variant,
)
from . import screens
from .guide_parts import (
    BATTERY,
    CONDUCTORS,
    L_LEAD,
    LIVE,
    LIVE_PARTS,
    N_LEAD,
    NEXT_PAIR,
    PATH,
    PE_BAR,
    PE_LEAD,
    SOFTKEYS,
    STORE,
    SWITCH,
    flow,
)

TO_L1 = Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming line conductor L1."))
NOTE = N_("Measures the voltage between the probes and its frequency.")
PRINTED = ("nominal_voltage", "rated_current")

SINGLE = Guide(
    "u", N_("Voltage"), 12, *SWITCH, (PE_BAR, TO_L1), LIVE_PARTS,
    element_features=CONDUCTORS, live=True, preparation=(LIVE,), selector_label="U",
    selector_note=NOTE, settings=(Action((), PATH, screens.U_PATH),),
    steps=(Action((), N_("Hold the probes in place: the measurement starts by itself and the"
                         " voltage is shown at once.")), STORE, NEXT_PAIR),
    screen=screens.U, result_key=screens.RESULT, drawing_features=PRINTED, every_path=True,
    flow=flow())
N_ASIDE = Action((), N_("Take probe N (L3) off and put it aside: the view U measures between"
                        " the probes L and PE only."))
AFTER_LINES = replace(
    SINGLE,
    settings=(Action((), N_("View: switch back to U with the top softkey."), screens.VIEW_U),
              *SINGLE.settings),
    flow=(Station(CONNECT, N_("Leads to L1 and PE"), (N_ASIDE,)),
          Station(CONFIGURE, N_("Measuring path"), (SOFTKEYS,), zoom=("lcd",)),
          Station(MEASURE, N_("Single voltages"))))
THREE_PHASE = Guide(
    "u3", N_("Voltage and phase sequence"), 12, *SWITCH,
    (TO_L1,
     Lead(*PE_LEAD, "in_l2", N_("Place probe PE (L2) on the incoming line conductor L2.")),
     Lead(*N_LEAD, "in_l3", N_("Place probe N (L3) on the incoming line conductor L3."))),
    LIVE_PARTS, element_features=CONDUCTORS, live=True, preparation=(LIVE,), selector_label="U",
    selector_note=NOTE,
    settings=(Action((), N_("View: choose U3~ with its softkey. It shows the three voltages"
                            " between the line conductors and the phase sequence."),
                     screens.VIEW_U3),),
    steps=(Action((), N_("Hold the probes in place: the voltages and the phase sequence are"
                         " shown at once.")), STORE),
    screen=screens.U3, result_key=screens.RESULT, drawing_features=PRINTED,
    flow=(Station(PLACE), Station(SELECT, N_("Rotary switch")),
          Station(CONNECT, N_("Leads to L1, L2 and L3")), Station(PREPARE, N_("Supply"), BATTERY),
          Station(CONFIGURE, N_("View U3~"), (SOFTKEYS,), zoom=("lcd",)),
          Station(MEASURE, N_("Line voltages"))),
    follow=AFTER_LINES)
VOLTAGE = replace(SINGLE, variants=(Variant(CONDUCTORS[0], "3", THREE_PHASE),))
