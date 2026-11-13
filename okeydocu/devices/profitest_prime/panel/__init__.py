# OkeyDocu - okeydocu/devices/profitest_prime/panel/__init__.py
# Where the parts of the PROFITEST PRIME's front panel are in its drawing.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""`front.svg` and `knob.svg` are written by `tools/panel-svg.py` from these numbers. The dial
has 24 detents, 15° apart, clockwise from OFF at the top; each is known by the value the
instrument reports for it."""

from importlib import resources

FOLDER = resources.files(__name__)
FRONT = FOLDER / "front.svg"
KNOB = FOLDER / "knob.svg"

DIAL = (885.0, 548.0)  # centre of the dial in the drawing
KNOB_RADIUS = 75.0
DIAL_REACH = 135.0  # a click this far from the centre still turns the dial
STEP_DEGREES = 15.0
# Detent 0 is OFF; detents 1 to 23 report 12 to 34, OFF reports 35.
VALUES = [35] + list(range(12, 35))


def angle_of(value: int) -> float | None:
    """Degrees clockwise from the top for a reported value, None for an unknown one."""
    return VALUES.index(value) * STEP_DEGREES if value in VALUES else None


def value_at(degrees: float) -> int:
    """The detent nearest to an angle, clockwise from the top."""
    return VALUES[round((degrees % 360) / STEP_DEGREES) % len(VALUES)]
