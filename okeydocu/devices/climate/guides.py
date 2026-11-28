# OkeyDocu - okeydocu/devices/climate/guides.py
# The guided measurement of the surroundings with a climate sensor.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Air temperature and humidity tell under which conditions the readings of a test were
taken. No standard sets a limit for them: PROFITEST PRIME and its kind measure as specified
between 0 and 35 degrees (VDE 0413), and the resistance of insulation and protective conductors
depends on temperature, so a figure far from 20 degrees is worth noting beside them (VDE 0100-600,
national note to 6.4.3.2). The sensor is pointed out first, since several may be in reach, then
laid out in free air and watched until its readings stand."""

from __future__ import annotations

from ...l10n import N_
from ..guide import IDENTIFY, MEASURE, PLACE, PREPARE, SETTLE, Action, Guide, Station

IDENTIFIED = Action((), N_("Click \u201cIdentify sensor\u201d. Within a few seconds the"
                           " sensor in question shows the number named here with a face."))
PLACED = (
    Action((), N_("Lay the sensor out at the equipment tested, at about the height of the"
                  " parts measured.")),
    Action((), N_("Keep a hand's width from the equipment and out of the warm air of its vents,"
                  " out of sun, draught and the warmth of your hand.")),
)
TAKEN = Action((), N_("Click \u201cTake reading\u201d: the latest reading of the sensor is"
                      " stored with the element chosen."))
FLOW = (Station(PLACE), Station(IDENTIFY, actions=(IDENTIFIED,)),
        Station(PREPARE, N_("Lay out"), actions=PLACED), Station(SETTLE), Station(MEASURE))

GUIDES = {guide.function: guide for guide in (
    Guide("ambient", N_("Ambient conditions"), None, "climate_sensor",
          N_("Air beside the equipment"), (), live=None, steps=(TAKEN,), flow=FLOW),
)}


def guide_for(function: str) -> Guide | None:
    return GUIDES.get(function)


def hints(values: dict[str, float]) -> list[str]:
    """What the air temperature among `values` means for the test, as untranslated texts."""
    temperature = values.get("t_air")
    if temperature is None:
        return []
    found = []
    if not 0 <= temperature <= 35:
        found.append(N_("Outside 0 to 35 \u00b0C instruments for testing installations no"
                        " longer measure as specified (VDE 0413)."))
    if abs(temperature - 20) > 10:
        found.append(N_("Far from 20 \u00b0C: insulation and protective conductor resistances"
                        " depend on the temperature; note it beside them (VDE 0100-600)."))
    return found
