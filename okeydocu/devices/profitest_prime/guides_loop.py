# OkeyDocu - okeydocu/devices/profitest_prime/guides_loop.py
# The PROFITEST PRIME's guides for the loop impedance: one per dial position.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Four dial positions measure the loop impedance, each in its own way. The plain one sends the
full test current and is taken at the supply of the machine, where no RCD stands in front. The
other three are made for a circuit behind an RCD and are taken at its outgoing side: with a
direct current that saturates the RCD first, in two parts with the probes N and PE changed
over, or with a test current small enough for the RCD set. The second softkey row differs with
the position; the probes are those the instrument's own help shows for it."""

from __future__ import annotations

from ...l10n import N_
from ..guide import Action, Guide, Lead
from . import screens
from .guide_parts import (
    CONDUCTORS,
    L_LEAD,
    LIVE_PARTS,
    N_LEAD,
    NEXT_PAIR,
    PATH,
    PE_BAR,
    PE_LEAD,
    RCD_SIDE,
    START,
    STORE,
    SWITCH,
    flow,
)
from .guides_in_front import AT_SUPPLY, CHANGED_AT_SUPPLY, with_rcd_in_front
from .guides_rcd import LEADS, SECURE, TO_L

PRINTED = ("nominal_voltage", "rated_current")
STATED = ("rcd_type", "rated_residual_current", "number_of_poles", "n_terminal")
LIVE_LOOP = (N_("Leave it switched on"), N_("The loop is measured on the live supply."))
BEHIND = (
    LIVE_LOOP,
    (N_("Inform the operator"), N_("The RCD is not meant to trip, but it can: the circuit is"
                                   " then switched off.")),
    SECURE,
    (N_("Where to measure"), N_("The loop is greatest at the far end of the circuit: measure"
                                " there where possible.")),
)
DEVICE = Action((), N_("Protective device: rated current and characteristic of the fuse or"
                       " breaker in front; cross-section, cable and cores are for the record."),
                screens.DEVICE)
JUDGED = Action((), N_("Limits: the touch voltage and how the short-circuit current is judged."),
                screens.Z_LIMITS)
RCD_DATA = Action((), N_("RCD: its rated residual current and type, or it trips while"
                         " measuring."), screens.RCD)
NEXT_LINE = Action(("key-idn",), N_(
    "For further line conductors move probe L to the one the display names. IΔN skips a pair"
    " the test point does not have."))
LOOPS_ONLY = Action((), N_(
    "Only a line conductor against PE is a loop: L1-PE, L2-PE, L3-PE. The display goes on to"
    " L1-N and to pairs of line conductors: skip these with IΔN, the probes N and PE stay where"
    " they are. The line impedance L-N is taken at the position ZLOOP with two probes, probe PE"
    " on N."))
LOOPS_OF_TWO = Action((), N_(
    "Only a line conductor against PE is a loop: L1-PE, L2-PE, L3-PE. The display goes on to"
    " L1-N and to pairs of line conductors: skip these with IΔN, probe PE stays on the PE bar."
    " The line impedance L-N is taken at the position ZLOOP, with probe PE on N."))
CHANGED_OVER = (
    Lead(*N_LEAD, "pe", N_("Place probe N (L3) on the PE bar: here N and PE change places.")),
    TO_L,
    Lead(*PE_LEAD, "out_n", N_("Place probe PE (L2) on the outgoing N terminal of the RCD.")))


def behind_rcd(function: str, title: str, selector: int, label: str, note: str, leads: tuple,
               own: Action, path, screen, caution: str = LIVE_PARTS) -> Guide:
    """A loop guide taken at the outgoing side of an RCD. `own` is the setting in the second
    softkey row, `path` the row of the measuring path at this position."""
    guide = Guide(
        function, title, selector, *RCD_SIDE, leads, caution, "rcd_type", STATED, True, BEHIND,
        label, note, settings=(DEVICE, own, JUDGED, Action((), PATH, path)),
        steps=(START, STORE, NEXT_LINE, LOOPS_ONLY if len(leads) > 2 else LOOPS_OF_TWO),
        screen=screen, result_key=screens.RESULT, every_path=True, flow=flow())
    supply = CHANGED_AT_SUPPLY if leads is CHANGED_OVER else AT_SUPPLY[:len(leads)]
    return with_rcd_in_front(guide, supply)


LOOP = Guide(
    "zloop", N_("Loop impedance"), 20, *SWITCH,
    (PE_BAR, Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming line conductor"
                                       " L1."))),
    LIVE_PARTS, element_features=CONDUCTORS, live=True,
    preparation=(LIVE_LOOP, (N_("Inform the operator"),
                             N_("An RCD in front may trip and switch the circuit off."))),
    selector_label="ZLOOP",
    selector_note=N_("Measures the loop impedance and the short-circuit current with the full"
                     " test current, which trips an RCD in front. Behind an RCD take one of the"
                     " three positions that follow; each has a guide of its own."),
    settings=(DEVICE, JUDGED, Action((), PATH, screens.Z_PATH)),
    steps=(START, STORE, NEXT_PAIR), screen=screens.ZLOOP, result_key=screens.RESULT,
    drawing_features=PRINTED, every_path=True, flow=flow())
LOOP_DC = behind_rcd(
    "zloop_dc", N_("Loop impedance behind an RCD: DC+"), 21, "ZLOOP+DC",
    N_("For a circuit behind an RCD of type A or F: a direct current saturates the RCD before"
       " half waves measure the loop, so it does not trip. Needs all three probes and N at the"
       " test point. It is the second of the four ZLOOP positions, marked DC+."),
    LEADS,
    Action((), N_("DC variant: DC-L measures faster, DC-H is safer against tripping the RCD."),
           screens.DC_VARIANT),
    screens.Z_PATH, screens.ZLOOP_DC)
LOOP_COMBINED = behind_rcd(
    "zloop_rlo", N_("Loop impedance behind an RCD: L-N and N-PE"), 22, "ZLOOP+RLO",
    N_("For a circuit behind an RCD of type A, F or B: L-N is measured with the full test"
       " current, N-PE with a small one, and both together make the loop. Needs all three"
       " probes and N at the test point, with the probes N and PE changed over. It is the"
       " third of the four ZLOOP positions."),
    CHANGED_OVER, RCD_DATA, screens.Z_PATH_RCD, screens.ZLOOP_COMBINED,
    N_("Probes N and PE change places for this measurement. Live parts are exposed: touch only"
       " the grips of the probes."))
LOOP_REDUCED = behind_rcd(
    "zloop_half", N_("Loop impedance behind an RCD: reduced test current"), 23,
    N_("ZLOOP+0.5x"),
    N_("For a circuit behind an RCD of type A or F: the test current stays small enough for"
       " the RCD set. Two probes are enough, but the reading is coarse: the instrument states"
       " its accuracy from 10 Ω up. It is the last of the four ZLOOP positions, marked with"
       " square pulses."),
    LEADS[:2], RCD_DATA, screens.Z_PATH, screens.ZLOOP_REDUCED)
