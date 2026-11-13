# OkeyDocu - okeydocu/ui/step_text.py
# How the setup of a measuring step reads on screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from ..campaign.plan import PlanStep
from ..l10n import N_, tr
from ..vocabulary import setting_name

PLATE = N_("as on the rating plate")
NO_RCD = N_("No RCD chosen: choose the RCD this test is for as the place of the reading.")
UNSTATED = N_("Enter what the rating plate says at {element}, so the next reading can be"
              " checked against it.")


def title_html(step: PlanStep) -> str:
    selector = tr("Rotary switch: {selector}", selector=f"<b>{escape(step.selector)}</b>")
    return f"<h3>{escape(step.title)}</h3>{selector}"


def settings_html(step: PlanStep, expected: list[tuple[str, str]] = (),
                  element: str | None = "") -> str:
    """`expected` is what the element the settings describe states for them, by key; a
    setting it does not state is read off the rating plate. `element` None means the chosen
    place has no such element, which a step deciding settings by its element warns about."""
    stated = dict(expected)
    pairs = [(setting_name(key) or key, stated.get(key) or tr(PLATE))
             for key in step.element_settings]
    items = "".join(f"<li>{escape(k)}: <b>{escape(v)}</b></li>"
                    for k, v in [*pairs, *step.settings])
    if not items:
        return ""
    title = (tr("Set on the instrument for {element}", element=escape(element))
             if element else tr("Set on the instrument"))
    html = f"<b>{title}</b><ul>{items}</ul>"
    if step.element_settings and element is None:
        html = f"<span style='color:#b03a2e'><b>⚠ {escape(tr(NO_RCD))}</b></span><br>" + html
    elif step.element_settings and element and len(stated) < len(step.element_settings):
        html += f"<i>{escape(tr(UNSTATED, element=element))}</i>"
    return html


def warnings_html(step: PlanStep) -> str:
    items = "".join(f"<li>{escape(text)}</li>" for text in step.warnings)
    if not items:
        return ""
    return f"<span style='color:#b03a2e'><b>{tr('Caution')}</b><ul>{items}</ul></span>"


def instructions_html(step: PlanStep) -> str:
    items = "".join(f"<li>{escape(text)}</li>" for text in step.instructions)
    dut = f"<b>{tr('Device under test')}</b><br>{escape(step.dut)}<br><br>" if step.dut else ""
    return f"{dut}<b>{tr('Procedure')}</b><ol>{items}</ol>" if items else dut


def source_html(step: PlanStep) -> str:
    if not step.source:
        return ""
    return f"<small>{tr('Source: {source}', source=escape(step.source))}</small>"
