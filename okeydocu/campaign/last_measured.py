# OkeyDocu - okeydocu/campaign/last_measured.py
# The element a campaign last booked a reading of a guided measurement to.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A guide counts every reading its own run can end with: its own function and results, those
of the variants that take over for an element and of the guides that follow in the run."""

from __future__ import annotations

from ..devices.guide import Guide


def functions_of(guide: Guide) -> set[str]:
    """The functions of the readings a run of `guide` can end with."""
    found: set[str] = set()
    for start in (guide, *(variant.guide for variant in guide.variants)):
        for link in start.chain():
            found |= {link.function, *link.results}
    return found


def last_measured_at(db, campaign_id: int, guide: Guide) -> int | None:
    """The element of the campaign's latest reading `guide` stands for, if one is assigned."""
    names = sorted(functions_of(guide))
    marks = ",".join("?" * len(names))
    row = db.one("SELECT asset_id FROM measurements WHERE campaign_id=? AND asset_id IS NOT NULL"
                 f" AND function IN ({marks}) ORDER BY local_time DESC, id DESC LIMIT 1",
                 campaign_id, *names)
    return row["asset_id"] if row is not None else None
