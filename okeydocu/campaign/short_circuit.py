# OkeyDocu - okeydocu/campaign/short_circuit.py
# A short-circuit current measured at a machine, held against the rating the machine states.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The maker rates the electrical equipment of a machine for a short-circuit current
(EN 60204-1, 7.10), and the short-circuit current to be expected where it is connected must
not exceed that rating (7.2.9). That current belongs to the place, not to the machine: one
measured at the maker's works says nothing about the operator's supply. A reading above the
rating shows the rating to be too small for the supply measured at. A reading below it proves
nothing: between three line conductors more current flows than a loop measurement between two
conductors gives, and such a measurement may be off by up to 30 % (IEC 61557-3, 6.2)."""

from __future__ import annotations

from ..model import MeterMeasurement, Quantity

RATING = "short_circuit_rating"  # what the machine states, in kA
CURRENT = "ik"  # the short-circuit current of a loop measurement


def rating_of(stated: str) -> float | None:
    """The rating an element states, such as “10 kA”, in amperes; None where it states none."""
    found = Quantity.parse(stated.replace(" ", "")) if stated else None
    if found is None or not found.base_value or found.base_unit != "A":
        return None
    return found.base_value


def above_rating(measurement: MeterMeasurement, stated: str) -> list[tuple]:
    """The short-circuit currents of a measurement above the rating stated, as (label,
    reading, rating in kA)."""
    rating = rating_of(stated)
    if rating is None:
        return []
    found = []
    for result in measurement.results:
        value = result.quantity.base_value
        if result.key == CURRENT and result.quantity.base_unit == "A" and value is not None \
                and value > rating:
            found.append((result.label, result.quantity.raw, rating / 1000))
    return found
