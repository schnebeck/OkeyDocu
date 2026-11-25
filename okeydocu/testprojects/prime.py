# OkeyDocu - okeydocu/testprojects/prime.py
# The test project with a simulated PROFITEST PRIME.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The project lays out the invented plant of `plant.py` with two campaigns under way: the
annual inspection of the press with five readings and the inspection plan of a machine
assigned, and the first inspection of a machine without an RCD of its own, still empty. Both
measure with the simulated PROFITEST PRIME, which this project registers as an instrument that
can be chosen for further campaigns."""

from __future__ import annotations

from datetime import datetime, time

from ..devices import register_driver
from ..devices.profitest_prime.simulated import DRIVER, KEY, SimulatedPrime
from ..l10n import current
from . import plant


def prepare(context) -> None:
    register_driver(DRIVER)
    # Invented records are sealed without the key of the real ones: the password store of
    # the desktop is none of a test project's business.
    context.service.key_store = None
    if not context.db.customers():
        lay_out(context)


def lay_out(context) -> dict[str, int]:
    """The plant and its campaigns, in the language of the program where its words are known."""
    lang = current() if current() in plant.WORDS else "en"
    words = plant.WORDS[lang]
    ids = plant.plant(context, lang)
    ids["saw"] = plant.bare_machine(context, ids, lang)
    identity = SimulatedPrime().identify()
    annual = plant.open_campaign(context, ids, words["now"], lang, KEY, identity)
    plant.measure_round(context, annual, ids, datetime.combine(datetime.now().date(), time(9)),
                        count=5)
    plant.inspect(context, annual, context.service.plans())
    first = plant.open_campaign(context, ids, words["first"], lang, KEY, identity, "saw")
    return {**ids, "annual": annual, "first": first}
