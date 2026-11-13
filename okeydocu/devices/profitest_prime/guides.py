# OkeyDocu - okeydocu/devices/profitest_prime/guides.py
# The PROFITEST PRIME's side of guided first measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every test lead fills all three sockets of its row. Plug and probe are marked differently:
plug 1 carries probe L (L1), plug 2 probe N (L3), plug 3 probe PE (L2); the conductor in
brackets is the one the lead takes for a phase sequence test."""

from __future__ import annotations

from ...l10n import N_
from ..guide import Guide, Lead

L_LEAD = ("1", "socket-1", "L (L1)")
N_LEAD = ("2", "socket-2", "N (L3)")
PE_LEAD = ("3", "socket-3", "PE (L2)")

RCD_LEADS = (
    Lead(*PE_LEAD, "pe", N_("Place probe PE (L2) on the PE bar.")),
    Lead(*L_LEAD, "out_l", N_("Place probe L (L1) on outgoing terminal 2 of the RCD.")),
    Lead(*N_LEAD, "out_n", N_("Place probe N (L3) on outgoing terminal N of the RCD.")),
)

RCD_FEATURES = ("rcd_type", "rated_residual_current", "rated_current", "number_of_poles",
                "n_terminal")
LIVE_RCD = (
    (N_("Inform the operator"), N_("The test switches the circuit off.")),
    (N_("Secure the loads"), N_("Save data, stop running machines.")),
    (N_("Leave it switched on"), N_("The RCD and the circuit stay on.")),
)

GUIDES = {
    "rcd_time": Guide(
        "rcd_time", N_("RCD tripping test IΔN"), 18, "rcd",
        N_("RCD, outgoing side"), RCD_LEADS,
        N_("The test switches the circuit off. Secure the loads beforehand."),
        "rcd_type", RCD_FEATURES, True, LIVE_RCD),
}


def guide_for(function: str) -> Guide | None:
    return GUIDES.get(function)
