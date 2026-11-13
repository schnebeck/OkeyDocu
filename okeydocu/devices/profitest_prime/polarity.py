# OkeyDocu - okeydocu/devices/profitest_prime/polarity.py
# The protective conductor resistance in both current directions, as the vocabulary wants it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The PROFITEST PRIME measures RLO in both current directions and sends both figures, the
value it derives from them and their difference. The vocabulary's contract for `rlo` is:

    equal directions   rlo alone, the value both agree on
    other directions   rlo_plus and rlo_minus, the higher first: it is the reference, judged
                       by the limit of rlo; the lower is named beside it

A difference between the directions points to something other than plain resistance, such as
a contact that rectifies, so a single value would hide it. Neither the difference nor a
derived rlo is delivered then, so no reading shows all three figures."""
from __future__ import annotations

from dataclasses import replace

from ...model import ResultValue
from ...vocabulary import plain, vocabulary

MAIN, PLUS, MINUS, DELTA = "rlo", "rlo_plus", "rlo_minus", "rlo_delta"
DIRECTED = (MAIN, PLUS, MINUS, DELTA)


def _judged(reference: ResultValue, main: ResultValue | None) -> ResultValue:
    """The reference with the limit and verdict of rlo, where it has none of its own."""
    if main is None or reference.lower_limit or reference.upper_limit:
        return reference
    return replace(reference, lower_limit=main.lower_limit, upper_limit=main.upper_limit,
                   verdict=main.verdict)


def _agreed(plus: ResultValue, main: ResultValue | None) -> ResultValue:
    """rlo as the instrument sent it, where it says what both directions say."""
    if main is not None and main.quantity.base_value == plus.quantity.base_value:
        return main
    label = plain(vocabulary().results[MAIN].symbol)
    return _judged(replace(plus, key=MAIN, label=label), main)


def by_direction(results: tuple[ResultValue, ...]) -> tuple[ResultValue, ...]:
    """The figures of an RLO measurement as the contract says; others pass unchanged."""
    found = {result.key: result for result in results}
    plus, minus = found.get(PLUS), found.get(MINUS)
    if plus is None or minus is None or None in (plus.quantity.base_value,
                                                  minus.quantity.base_value):
        return results
    main = found.get(MAIN)
    if plus.quantity.base_value == minus.quantity.base_value:
        directed = [_agreed(plus, main)]
    else:
        higher, lower = sorted((plus, minus), key=lambda r: r.quantity.base_value, reverse=True)
        directed = [_judged(higher, main), lower]
    at = next(n for n, result in enumerate(results) if result.key in DIRECTED)
    others = [result for result in results if result.key not in DIRECTED]
    return tuple(others[:at] + directed + others[at:])
