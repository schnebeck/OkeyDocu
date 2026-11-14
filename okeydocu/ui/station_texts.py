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


def supply_text(guide: Guide) -> str:
    if guide.mains:
        lines = (tr("This measurement needs the mains."),
                 tr("Plug the mains lead into the inlet at the top right and switch on: 0 → I."),
                 tr("The MAINS lamp lights up."))
    else:
        lines = (tr("The battery is enough for this measurement."),
                 tr("Look at the BAT symbol at the top of the display. With a nearly empty"
                    " battery plug in the mains lead and switch on."))
    return "".join(f"<p>{escape(line)}</p>" for line in lines)


def conductors_text(guide: Guide, lines: str, has_n: bool | None) -> str:
    """Advice where AUTO would measure conductors the test point lacks."""
    if not guide.every_path or (lines != "1" and has_n is not False):
        return ""
    advice = tr("The test point lacks conductors AUTO would measure: choose the measuring path"
                " by hand. Readings against missing conductors are marked as not applicable.")
    return f"<p style='color:{CAUTION}'>⚠ {escape(advice)}</p>"


def mode_text(guide: Guide, settings: list[tuple[str, str]], element: str,
              advice: str = "") -> str:
    """`settings` are what the element states for the measurement, as (name, value);
    `advice` stands below the settings."""
    how = escape(tr("Press the softkey beside a setting, choose the value with the arrow"
                    " keys, confirm it and take it over with ✓."))
    items = "".join(f"<li>{escape(tr(action.text))}</li>" for action in guide.settings)
    stated = "".join(f"<li>{escape(name)}: <b>{escape(value)}</b></li>"
                     for name, value in settings)
    html = f"<ol>{items}</ol><p>{how}</p>{advice}"
    if stated:
        title = escape(tr("{element} states:", element=element))
        html += f"<p><b>{title}</b></p><ul>{stated}</ul>"
    return html


def measure_text(guide: Guide, reading=None) -> str:
    steps = "".join(f"<li>{escape(tr(action.text))}</li>" for action in guide.steps)
    if reading is None:
        waiting = escape(tr("Waiting for the result …"))
        return f"<ol>{steps}</ol><p><i>{waiting}</i></p>"
    values = "&nbsp;&nbsp; ".join(f"{escape(r.label)} <b>{escape(r.quantity.raw)}</b>"
                                  for r in reading.measurement.results[:3])
    received = escape(tr("Received"))
    done = escape(tr("Further measurements of this kind go straight to the chosen element."))
    return (f"<ol>{steps}</ol><p style='color:{RIGHT}'><b>✓ {received}:</b> {values}</p>"
            f"<p>{done}</p>")
