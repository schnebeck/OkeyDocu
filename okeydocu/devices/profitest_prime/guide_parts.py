# OkeyDocu - okeydocu/devices/profitest_prime/guide_parts.py
# What the PROFITEST PRIME's guides have in common: leads, supply, flow and standing words.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every test lead fills all three sockets of its row. Plug and probe are marked differently:
plug 1 carries probe L (L1), plug 2 probe N (L3), plug 3 probe PE (L2); the conductor in
brackets is the one the lead takes for a phase sequence test. A measurement is started with
ON/START, the fourth key left of the display; once a result stands, the lowest softkey shares
it over Push/Print. The measurements run on the battery unless a guide names the mains as its
supply.

Two-pole measurements name the pair of conductors the probes are on as their measuring path. It
is for the record only, the instrument switches nothing; with AUTO it names the pairs one after
the other and moves on with each reading stored."""

from __future__ import annotations

from ...l10n import N_
from ..guide import (
    CONFIGURE,
    CONNECT,
    MEASURE,
    PLACE,
    PREPARE,
    SELECT,
    Action,
    Lead,
    Station,
)

L_LEAD = ("1", "socket-1", "L (L1)")
N_LEAD = ("2", "socket-2", "N (L3)")
PE_LEAD = ("3", "socket-3", "PE (L2)")
PE_BAR = Lead(*PE_LEAD, "pe", N_("Place probe PE (L2) on the PE bar."))

STORE = Action(("soft-5",), N_("Press the share softkey at the bottom right: the instrument"
                                " prints the result to OkeyDocu and keeps nothing."))
BATTERY = (Action((), N_("The battery is enough for this measurement.")),
           Action(("mains-inlet", "mains-switch"),
                  N_("With a nearly empty battery plug the mains lead into the inlet at the top"
                     " right and switch on: 0 → I. The BAT symbol at the top of the display"
                     " shows how full the battery is.")))
MAINS = (Action(("mains-inlet", "mains-switch"), N_("This measurement needs the mains.")),
         Action((), N_("Plug the mains lead into the inlet at the top right and switch on:"
                       " 0 → I.")),
         Action((), N_("The red glow lamp of the switch lights up.")))
SOFTKEYS = Action((), N_("Press the softkey beside a setting, choose the value with the arrow"
                         " keys, confirm it and take it over with ✓."))


def flow(supply=BATTERY) -> tuple[Station, ...]:
    """The PROFITEST PRIME's six stations; `supply` says what the instrument runs on."""
    return (Station(PLACE), Station(SELECT, N_("Rotary switch")), Station(CONNECT),
            Station(PREPARE, N_("Supply"), supply),
            Station(CONFIGURE, N_("Mode and limits"), (SOFTKEYS,), zoom=("lcd",)),
            Station(MEASURE))


LIMITS = N_("Limits: set them as the test basis requires.")
PATH = N_("Measuring path: it only names the two conductors the probes are on; the instrument"
          " switches nothing. With AUTO the display names the pair to measure, L1-PE first, and"
          " moves on to the next with each reading stored.")
NEXT_PAIR = Action(("key-idn",), N_(
    "For further pairs of conductors move the two probes to the pair the display names. IΔN"
    " skips a pair the test point does not have."))
START = Action(("key-start",), N_("With the probes in place press ON/START and hold them until"
                                  " the result stands."))
LIVE = (N_("Leave it switched on"), N_("The voltage is measured on the live supply."))
LIVE_PARTS = N_("Live parts are exposed: touch only the grips of the probes.")
CONDUCTORS = ("line_conductors", "n_conductor")  # what reaches the test point
SWITCH = ("main_switch", N_("Main switch, incoming terminals"))
RCD_SIDE = ("rcd", N_("RCD, outgoing side"))
PLUG_OFF = N_("Switch off and pull the plug")
