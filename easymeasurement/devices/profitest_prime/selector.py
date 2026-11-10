# EasyMeasurement - easymeasurement/devices/profitest_prime/selector.py
# What the positions of the PROFITEST PRIME's rotary switch mean.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..base import SelectorPosition

SELECTOR_COMMAND = "SYS:GET:ROTATIONWHEEL"

_ZLOOP = ("zloop", "zloop_dc", "zloop_rlo", "zloop_half")

# Position to label and the functions it can produce. No functions means the position
# says nothing about the measurement: Extra and HV hold a list, a sequence brings its own.
_POSITIONS = {
    12: ("U", ("u", "u3")),
    13: ("RLO", ("rlo",)),
    14: ("RLO-25A", ("rlo_25a",)),
    15: ("RISO", ("riso",)),
    16: ("RISO-Rampe", ("riso_ramp",)),
    17: ("IF", ("rcd_current", "rcd_ramp_touch")),
    18: ("IΔN", ("rcd_time", "rcd_touch")),
    19: ("I_RAMP", ("i_ramp",)),
    20: ("ZLOOP", _ZLOOP),
    21: ("ZLOOP+DC", _ZLOOP),
    22: ("ZLOOP+RLO", _ZLOOP),
    23: ("ZLOOP+0,5x", _ZLOOP),
    24: ("URES", ("ures",)),
    25: ("IMD", ("imd",)),
    26: ("RCM", ("rcm_touch",)),
    27: ("IL", ("il",)),
    28: ("I_ZANGE", ("i_clamp",)),
    29: ("T%rH", ()),
    30: ("Extra", ()),
    31: ("HV", ()),
    32: ("Auto", ()),  # test sequences: the step decides what is measured
    33: ("Setup", ()),
    34: ("Batteriezustand", ()),
    35: ("OFF", ()),
}


def selector_position(value: int) -> SelectorPosition:
    """Named as printed on the dial. Positions without a measuring function, such as
    Setup, rule nothing out; an unknown value has no name."""
    label, functions = _POSITIONS.get(value, ("", ()))
    return SelectorPosition(label, frozenset(functions))
