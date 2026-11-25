# OkeyDocu - okeydocu/devices/profitest_prime/guides_in_front.py
# RCD tests and loops behind an RCD that stands in front of the installation.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A measurement that needs an RCD is taken at the RCD where that is an element of the
installation. An RCD of the building installation stands in front of the installation and is
none of its elements: the same measurement is then taken at the supply, on the incoming
terminals of the main switch, and belongs to the element it is taken for."""

from __future__ import annotations

from dataclasses import replace

from ...l10n import N_
from ..guide import IN_FRONT, RCD_PLACE, Guide, Lead, Variant
from .guide_parts import L_LEAD, N_LEAD, PE_BAR, PE_LEAD, SWITCH

IN_L1 = Lead(*L_LEAD, "in_l1", N_("Place probe L (L1) on the incoming line conductor L1."))
AT_SUPPLY = (PE_BAR, IN_L1,
             Lead(*N_LEAD, "in_n", N_("Place probe N (L3) on the incoming N terminal.")))
# For the loop in two parts, where the probes N and PE change places.
CHANGED_AT_SUPPLY = (
    Lead(*N_LEAD, "pe", N_("Place probe N (L3) on the PE bar: here N and PE change places.")),
    IN_L1,
    Lead(*PE_LEAD, "in_n", N_("Place probe PE (L2) on the incoming N terminal.")))
TEST_POINT = N_("Main switch, incoming terminals; the RCD stands in front")


def with_rcd_in_front(guide: Guide, leads: tuple[Lead, ...]) -> Guide:
    """`guide` with the variant an element takes that states its RCD in front: the probes go
    to the main switch as `leads` say, and the drawing prints the voltage, not an RCD."""
    at_supply = replace(guide, test_object=SWITCH[0], test_point=TEST_POINT, leads=leads,
                        drawing_features=("nominal_voltage",))
    return replace(guide, variants=(*guide.variants, Variant(RCD_PLACE, IN_FRONT, at_supply)))
