# OkeyDocu - okeydocu/devices/profitest_prime/guides_residual.py
# The PROFITEST PRIME's guide for the residual voltage after switching off.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The residual voltage is watched at the outgoing side of the main switch while it is switched
off; the instrument starts its clock by itself."""

from __future__ import annotations

from ...l10n import N_
from ..guide import Action, Guide, Lead
from . import screens
from .guide_parts import CONDUCTORS, L_LEAD, LIVE_PARTS, PE_BAR, STORE, flow

PRINTED = ("nominal_voltage", "rated_current")
RESIDUAL = Guide(
    "ures", N_("Residual voltage"), 24, "main_switch", N_("Main switch, outgoing terminals"),
    (PE_BAR, Lead(*L_LEAD, "out_l1", N_("Place probe L (L1) on the outgoing terminal of line"
                                        " conductor L1."))),
    LIVE_PARTS, element_features=CONDUCTORS, live=True,
    preparation=((N_("Leave it switched on"),
                  N_("The measurement starts from the running machine.")),),
    selector_label="Ures",
    selector_note=N_("Measures the voltage left after switching off and the time it takes to"
                     " fall."),
    settings=(Action((), N_("Limits: 60 V after 5 s for a machine; 1 s where pulling a plug"
                            " bares its contacts."), screens.LIMITS),),
    steps=(Action((), N_("Hold the probes in place: the voltage is shown, nothing needs to be"
                         " pressed.")),
           Action((), N_("Switch the main switch off: the instrument notices the voltage"
                         " falling, stops the time and shows the residual voltage.")),
           STORE, Action(("key-esc",), N_("ESC clears the values for another run."))),
    screen=screens.URES, result_key=screens.RESULT, drawing_features=PRINTED, flow=flow())
