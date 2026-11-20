# OkeyDocu - okeydocu/devices/profitest_prime/guides_current.py
# The PROFITEST PRIME's guides for small currents: at a touchable part and with a clamp.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Both measure on the running machine and go on measuring until the reading is shared. The
current at a touchable part flows through the instrument to the PE bar, as it would through a
person. The clamp takes no test lead: it has a socket of its own and closes around the
protective conductor, or around the line conductors and N together for the residual current."""

from __future__ import annotations

from ...l10n import N_
from ..guide import CLAMP, Action, Guide, Lead
from . import screens
from .guide_parts import L_LEAD, PE_BAR, STORE, flow

ON = N_("Leave it switched on")
TOUCH_CURRENT = Guide(
    "il", N_("Leakage current at touchable parts"), 27, "touchable_part",
    N_("Touchable part of the machine"),
    (PE_BAR, Lead(*L_LEAD, "part", N_("Touch the conductive part with probe L (L1): one that"
                                      " is not connected to the protective conductor."))),
    N_("Make sure first that the part carries no voltage: above 60 V the instrument switches"
       " the measurement off."),
    live=True,
    preparation=((ON, N_("The current flows only while the machine runs.")),),
    selector_label="IL",
    selector_note=N_("Measures the current that flows from a touchable conductive part to"
                     " earth through 2 kΩ, as through a person touching it."),
    settings=(Action((), N_("Limits: the current the standard of the equipment allows."),
                     screens.LIMITS),),
    steps=(Action(("key-start",), N_("With the probes in place press ON/START: the current is"
                                     " measured on and on.")),
           Action((), N_("Touch further parts with probe L one after the other.")), STORE),
    screen=screens.IL, result_key=screens.RESULT, flow=flow())
CLAMP_CURRENT = Guide(
    "i_clamp", N_("Current with a clamp"), 28, "supply_cores",
    N_("Supply cable of the machine, cores spread"),
    (Lead("", "socket-clamp", "", "pe_core",
          N_("Plug the clamp into the round socket above the test lead sockets and close it"
             " around the protective conductor alone."), CLAMP),),
    N_("Use only a clamp made for this instrument: the socket stands 1 V at most."),
    live=True,
    preparation=((ON, N_("The current flows only while the machine runs.")),),
    selector_label=N_("I_CLAMP"),
    selector_note=N_("Measures a current with a clamp: the leakage current in the protective"
                     " conductor, or the residual current with the clamp around the line"
                     " conductors and N together. On the dial the position is marked ≤1V."),
    settings=(Action((), N_("Ratio: as the switch of the clamp stands; the leakage current"
                            " clamp gives 100 mV/mA."), screens.CLAMP_RATIO),
              Action((), N_("Limits: the current allowed."), screens.LIMITS)),
    steps=(Action(("key-start",), N_("Press ON/START: the current is measured on and on.")),
           Action((), N_("For the residual current close the clamp around the line conductors"
                         " and N together, without the protective conductor.")), STORE),
    screen=screens.I_CLAMP, result_key=screens.RESULT, flow=flow())
