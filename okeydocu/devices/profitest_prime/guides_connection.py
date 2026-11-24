# OkeyDocu - okeydocu/devices/profitest_prime/guides_connection.py
# The dead measurements at another supply connection: a Schuko plug, or terminals.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The protective conductor and the insulation guides are drawn at a CEE plug. Where the
element states another supply connection, a variant takes over with the same settings:

- at a Schuko plug its earthing clip is the PE contact; the pins have no fixed L and N, so the
  insulation is measured from pin 1 and then from pin 2;
- at a fixed connection the protective conductor is measured from the PE bar the supply comes
  in on to the housing; the insulation at the incoming terminals of the main switch, with the
  supply switched off in front of it and the main switch on, so the circuits behind it are
  measured too."""

from __future__ import annotations

from dataclasses import replace

from ...l10n import N_
from ..guide import Guide, Lead, Variant
from .guide_parts import L_LEAD, PE_BAR, PE_LEAD
from .guides_resistance import HIGH_CURRENT, INSULATION, PROTECTIVE_CONDUCTOR, RISING

CONNECTION = "supply_connection"
HOUSING = Lead(*PE_LEAD, "body", N_("Place probe PE (L2) on a bare metal spot of the housing."))
CONDUCTOR_AT_SCHUKO = (
    Lead(*L_LEAD, "pe_pin", N_("Place probe L (L1) on an earthing clip of the Schuko plug.")),
    HOUSING)
INSULATION_AT_SCHUKO = (
    Lead(*PE_LEAD, "pe_pin", N_("Place probe PE (L2) on an earthing clip of the Schuko plug.")),
    Lead(*L_LEAD, "l_pin", N_("Place probe L (L1) on pin 1 of the Schuko plug, then on pin 2:"
                              " either may be L.")))
CONDUCTOR_AT_TERMINALS = (
    Lead(*L_LEAD, "pe", N_("Place probe L (L1) on the PE bar the supply comes in on.")),
    HOUSING)
INSULATION_AT_TERMINALS = (
    PE_BAR,
    Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming terminal of line conductor"
                              " L1.")))
FIXED_INSULATION = (
    (N_("Switch off in front"), N_("Switch the supply off ahead of the machine and secure"
                                   " it.")),
    (N_("Switch the machine's main switch on"),
     N_("So the circuits behind it are measured too.")),
    (N_("Open the N-PE bridge"), N_("Where N and PE are bridged at the supply, open the"
                                    " bridge.")),
    (N_("Mind sensitive parts"),
     N_("Disconnect what the test voltage would damage, or lower it.")))


def at_schuko(guide: Guide, leads: tuple[Lead, ...], test_point: str) -> Variant:
    return Variant(CONNECTION, "Schuko plug", replace(
        guide, test_object="schuko_plug", test_point=test_point, leads=leads))


def at_terminals(guide: Guide, test_object: str, leads: tuple[Lead, ...], test_point: str,
                 preparation: tuple, caution: str = "") -> Variant:
    fixed = replace(guide, test_object=test_object, test_point=test_point, leads=leads,
                    preparation=preparation, caution=caution or guide.caution)
    return Variant(CONNECTION, "fixed", fixed)


def conductor(guide: Guide) -> Guide:
    return replace(guide, variants=(
        at_schuko(guide, CONDUCTOR_AT_SCHUKO, N_("Schuko plug and housing of the machine")),
        at_terminals(guide, "supply_pe", CONDUCTOR_AT_TERMINALS,
                     N_("PE bar of the supply and housing of the machine"),
                     ((N_("Switch off in front"),
                       N_("The protective conductor is measured without voltage.")),
                      (N_("Find a bare metal spot"),
                       N_("Paint and rust falsify the result."))),
                     N_("Measure only dead: the supply is switched off in front."))))


def insulation(guide: Guide) -> Guide:
    return replace(guide, variants=(
        at_schuko(guide, INSULATION_AT_SCHUKO, N_("Schuko plug of the machine, pulled")),
        at_terminals(guide, "main_switch_on", INSULATION_AT_TERMINALS,
                     N_("Main switch, incoming terminals, supply switched off"),
                     FIXED_INSULATION)))


PROTECTIVE_CONDUCTOR = conductor(PROTECTIVE_CONDUCTOR)
HIGH_CURRENT = conductor(HIGH_CURRENT)
INSULATION = insulation(INSULATION)
RISING = insulation(RISING)
