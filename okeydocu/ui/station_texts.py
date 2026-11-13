# OkeyDocu - okeydocu/ui/station_texts.py
# What the right side of the guided measurement says, station by station.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from ..devices.guide import Guide
from ..l10n import tr

CAUTION = "#b03a2e"
RIGHT = "#2e8b57"


def fits(guide: Guide, position) -> bool:
    """Whether the reported dial position serves the guide's measurement: the target itself,
    or one that also produces its function."""
    return position is not None and (position.value == guide.selector
                                     or guide.function in position.functions)


def dial_text(guide: Guide, position) -> str:
    turn = tr("Turn the rotary switch to {position}.", position="§")
    turn = escape(turn).replace("§", f"<b>{escape(guide.selector_label)}</b>")
    note = f"<p>{escape(tr(guide.selector_note))}</p>" if guide.selector_note else ""
    if position is None:
        alone = tr("No instrument connected: turn the switch, then go on.")
        state = f"<p><i>{escape(alone)}</i></p>"
    elif fits(guide, position):
        state = f"<p style='color:{RIGHT}'><b>✓ {escape(tr('The switch is set right.'))}</b></p>"
    else:
        where = position.label or tr("a position without a measurement")
        state = (f"<p style='color:{CAUTION}'><b>"
                 f"{escape(tr('The instrument is set to {position}.', position=where))}</b></p>")
    return f"<p>{turn}</p>{note}{state}"


def leads_text(guide: Guide) -> str:
    steps = "".join(f"<li>{escape(tr(lead.text))}</li>" for lead in guide.leads)
    plugs = ", ".join(lead.plug for lead in sorted(guide.leads, key=lambda lead: lead.plug))
    caution = (f"<p style='color:{CAUTION}'>⚠ {escape(tr(guide.caution))}</p>"
               if guide.caution else "")
    plugged = tr("Leads {plugs} are plugged into their rows of sockets.", plugs=plugs)
    return f"<p>{escape(plugged)}</p><ol>{steps}</ol>{caution}"


def later_text() -> str:
    return f"<i>{escape(tr('This station follows.'))}</i>"
