# OkeyDocu - okeydocu/devices/simulator_guides.py
# The simulator's guided measurements: a short flow of its own, without a panel or leads.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The simulator has no front panel and nothing to connect: its function is chosen in the
campaign window, and a click there sends a random result. Its flow therefore has three
stations, where the PROFITEST PRIME has six."""

from __future__ import annotations

from ..l10n import N_
from .guide import MEASURE, PLACE, SELECT, Action, Guide, Station

CHOOSE = Action((), N_("Choose the measurement in the campaign window, beside “Simulate"
                       " measurement”."))
SIMULATE = Action((), N_("Click “Simulate measurement”: the simulator sends a random result."))
FLOW = (Station(PLACE), Station(SELECT, actions=(CHOOSE,)), Station(MEASURE))


def _guide(function: str, title: str, drawing: str, test_point: str, **more) -> Guide:
    return Guide(function, title, None, drawing, test_point, (), steps=(SIMULATE,), flow=FLOW,
                 **more)


GUIDES = {guide.function: guide for guide in (
    _guide("rcd_time", N_("RCD tripping test IΔN"), "rcd", N_("RCD, outgoing side"),
           owner_feature="rcd_type", results=("rcd_touch",),
           element_features=("rcd_type", "rated_residual_current", "rated_current")),
    _guide("u", N_("Voltage"), "main_switch", N_("Main switch, incoming terminals")),
    _guide("rlo", N_("Protective conductor resistance"), "cee_plug",
           N_("CEE plug and housing of the machine"), live=False),
)}


def guide_for(function: str) -> Guide | None:
    return GUIDES.get(function)
