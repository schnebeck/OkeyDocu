# OkeyDocu - okeydocu/ui/station_texts.py
# What the right side of the guided measurement says, station by station.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from ..devices.guide import PROBE, Guide
from ..l10n import tr
from ..vocabulary.basis import basis_of

CAUTION = "#b03a2e"
RIGHT = "#2e8b57"
MUTED = "#5f666d"


def fits(guide: Guide, position) -> bool:
    """Whether the reported dial position serves the guide's measurement."""
    return position is not None and guide.served_at(position.value)


def dial_text(guide: Guide, position) -> str:
    turn = tr("Turn the rotary switch to {position}.", position="§")
    turn = escape(turn).replace("§", f"<b>{escape(tr(guide.selector_label))}</b>")
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


def basis_text(function: str) -> str:
    """The standards a measurement rests on and why it is taken."""
    basis = basis_of(function)
    if basis is None:
        return ""
    head = escape(tr("Basis"))
    standards = " · ".join(escape(standard) for standard in basis.standards)
    why = f"<p>{escape(tr(basis.why))}</p>" if basis.why else ""
    return f"<hr><p style='color:{MUTED}'><b>{head}:</b> {standards}</p>{why}"


def unsuited_text(function: str, stated) -> str:
    """A warning where the element, as `stated` tells by feature key, rules the method out."""
    basis = basis_of(function)
    advice = basis.unsuited_for(stated) if basis is not None else ""
    return f"<p style='color:{CAUTION}'>⚠ {escape(tr(advice))}</p>" if advice else ""


def further_text(function: str) -> str:
    """Where to measure next, once the instrument is set up."""
    basis = basis_of(function)
    if basis is None or not basis.further:
        return ""
    head = escape(tr("Where to measure next"))
    return f"<p><b>{head}:</b> {escape(tr(basis.further))}</p>"


def leads_text(guide: Guide) -> str:
    steps = "".join(f"<li>{escape(tr(lead.text))}</li>" for lead in guide.leads)
    plugs = ", ".join(sorted(lead.plug for lead in guide.leads if lead.tool == PROBE))
    caution = (f"<p style='color:{CAUTION}'>⚠ {escape(tr(guide.caution))}</p>"
               if guide.caution else "")
    plugged = tr("Leads {plugs} are plugged into their rows of sockets.", plugs=plugs)
    rows = f"<p>{escape(plugged)}</p>" if plugs else ""
    return f"{rows}<ol>{steps}</ol>{caution}"


def conductors_text(guide: Guide, lines: str, has_n: bool | None) -> str:
    """Advice where AUTO would name conductors the test point lacks."""
    if not guide.every_path or (lines != "1" and has_n is not False):
        return ""
    advice = tr("The test point lacks conductors AUTO would name: skip those pairs or choose"
                " the measuring path by hand. Readings against missing conductors are marked as"
                " not applicable.")
    return f"<p style='color:{CAUTION}'>⚠ {escape(advice)}</p>"


def actions_text(actions) -> str:
    """What a station asks for, one paragraph each."""
    return "".join(f"<p>{escape(tr(action.text))}</p>" for action in actions)


def mode_text(to_set, how, settings: list[tuple[str, str]], element: str,
              advice: str = "") -> str:
    """`to_set` are the settings of the measurement, `how` the station's own actions, such as
    how its keys set a value; `settings` what the element states for the measurement, as (name,
    value); `advice` stands below."""
    items = "".join(f"<li>{escape(tr(action.text))}</li>" for action in to_set)
    stated = "".join(f"<li>{escape(name)}: <b>{escape(value)}</b></li>"
                     for name, value in settings)
    html = (f"<ol>{items}</ol>" if items else "") + actions_text(how) + advice
    if stated:
        title = escape(tr("{element} states:", element=element))
        html += f"<p><b>{title}</b></p><ul>{stated}</ul>"
    return html


def measure_text(guide: Guide, reading=None, warnings=()) -> str:
    """`warnings` stand below a result received, such as a voltage that does not fit."""
    steps = "".join(f"<li>{escape(tr(action.text))}</li>" for action in guide.steps)
    if reading is None:
        waiting = escape(tr("Waiting for the result …"))
        return f"<ol>{steps}</ol><p><i>{waiting}</i></p>"
    values = "&nbsp;&nbsp; ".join(f"{escape(r.label)} <b>{escape(r.quantity.raw)}</b>"
                                  for r in reading.measurement.results[:3])
    received = escape(tr("Received"))
    done = escape(tr("Further measurements of this kind go straight to the chosen element."))
    warned = "".join(f"<p style='color:{CAUTION}'>⚠ {escape(text)}</p>" for text in warnings)
    return (f"<ol>{steps}</ol><p style='color:{RIGHT}'><b>✓ {received}:</b> {values}</p>"
            f"{warned}{further_text(guide.function)}<p>{done}</p>")
