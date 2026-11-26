# OkeyDocu - okeydocu/ui/limit_text.py
# The limit a guide proposes for a measurement, with the reckoning it comes from.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A proposal is made only from what the element states, and it says how it was reckoned, so
the inspector can check it and set it on the instrument. For the protective conductor two
things are told: what its length and cross-section let expect, and what supplementary
protective bonding may have at most with the protective device the element states."""

from __future__ import annotations

from html import escape

from ..campaign.bonding_limit import TOUCH_VOLTAGE, bonding_limit
from ..campaign.conductor_limit import CONTACTS, conductor_limit
from ..l10n import decimal, tr

PROTECTIVE_CONDUCTOR = ("rlo", "rlo_25a")
PROPOSED = "#1f6f8b"


def _ohms(value: float) -> str:
    return f"{decimal(value, 2)} Ω"


def _plain(value: float) -> str:
    """As short as the number allows: 5, 2.5, 0.75."""
    text = decimal(value, 2)
    return text.rstrip("0").rstrip(".,") if not value.is_integer() else decimal(value, 0)


def limit_text(function: str, stated, element: str, curve_of=None) -> str:
    """The proposals for `function` at the element that `stated` tells of, or nothing.
    `curve_of` gives the curve of a characteristic, where the caller knows the lists."""
    if function not in PROTECTIVE_CONDUCTOR:
        return ""
    return _conductor_text(stated, element) + _bonding_text(stated, curve_of)


def _bonding_text(stated, curve_of) -> str:
    found = bonding_limit(stated, curve_of) if curve_of else None
    if found is None:
        return ""
    head = tr("With supplementary protective bonding: at most {value}", value="§")
    how = tr("{characteristic} {rated} A trips at {current} A at the latest: {volts} V /"
             " {current} A. EN 60204-1, A.1.3, asks for this where the protective device"
             " cannot disconnect in time.",
             characteristic=found.characteristic, rated=_plain(found.rated),
             current=_plain(found.current), volts=_plain(TOUCH_VOLTAGE))
    head = escape(head).replace("§", f"<b>{escape(_ohms(found.value))}</b>")
    return f"<p style='color:{PROPOSED}'>{head}</p><p>{escape(how)}</p>"


def _conductor_text(stated, element: str) -> str:
    found = conductor_limit(stated)
    if found is None:
        return ""
    cable = tr("{length} m of {section} mm² copper", length=_plain(found.length),
               section=_plain(found.cross_section))
    if found.by_length:
        how = tr("{cable}: a cord of up to 1.5 mm² has its limit by its length.", cable=cable)
    else:
        how = tr("{cable}: {conductor} for the conductor plus {contacts} for the contacts.",
                 cable=cable, conductor=_ohms(found.conductor), contacts=_ohms(CONTACTS))
    if found.binding:
        head = tr("Proposed limit for {element}: {value}", element=element, value="§")
        how += " " + tr("Limit of the appliance tests (EN 50678 and EN 50699, 5.3). For a"
                        " machine they are a supplement the inspector decides on; EN 60204-1"
                        " sets no limit of its own.")
    else:
        head = tr("No fixed limit for {element}; to be expected: up to {value}",
                  element=element, value="§")
        how += " " + tr("EN 60204-1, 18.2.2, sets no limit: the reading has to fit length,"
                        " cross-section and material.")
    head = escape(head).replace("§", f"<b>{escape(_ohms(found.value))}</b>")
    return f"<p style='color:{PROPOSED}'>{head}</p><p>{escape(how)}</p>"
