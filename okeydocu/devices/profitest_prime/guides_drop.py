# OkeyDocu - okeydocu/devices/profitest_prime/guides_drop.py
# The PROFITEST PRIME's guide for the voltage drop along the supply.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The position Extra holds several functions; the top softkey chooses the voltage drop. The
instrument loads the supply between a line conductor and N, measures the line impedance and
works out the drop at the rated current of the fuse in front. With the offset the drop up to
the handover point is measured there once and left out of every reading after it."""

from __future__ import annotations

from ...l10n import N_
from ..guide import Action, Guide, Lead
from . import screens
from .guide_parts import (
    CONDUCTORS,
    L_LEAD,
    LIVE_PARTS,
    PE_LEAD,
    START,
    STORE,
    SWITCH,
    flow,
)

VOLTAGE_DROP = Guide(
    "zln_du", N_("Voltage drop ΔU"), 30, *SWITCH,
    (Lead(*PE_LEAD, "in_n", N_("Place probe PE (L2) on the incoming N.")),
     Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming line conductor L1."))),
    LIVE_PARTS, element_features=CONDUCTORS, live=True,
    preparation=((N_("Leave it switched on"),
                  N_("The voltage drop is measured on the live supply.")),),
    selector_label="Extra",
    selector_note=N_("Extra holds several functions. ΔU measures the line impedance between a"
                     " line conductor and N and works out the voltage drop at the rated current"
                     " of the fuse in front, in percent of the nominal voltage."),
    settings=(Action((), N_("Function: choose ΔU with the top softkey."), screens.EXTRA_MODE),
              Action((), N_("Circuit: the pair of conductors the probes are on, without N two"
                            " line conductors, and the rated current and characteristic of the"
                            " fuse in front; cross-section, cable and cores are for the"
                            " record."), screens.DU_CIRCUIT),
              Action((), N_("Limits: the voltage drop allowed in percent."), screens.LIMITS),
              Action((), N_("OFFSET: only to leave out the drop up to the handover point."
                            " Switch it on, place the probes at the meter, press IΔN and"
                            " confirm the prompt with IΔN again."), screens.DU_OFFSET)),
    steps=(START, STORE), screen=screens.DELTA_U, result_key=screens.RESULT,
    drawing_features=("nominal_voltage", "rated_current"), flow=flow())
