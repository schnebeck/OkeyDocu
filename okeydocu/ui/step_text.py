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


def title_html(step: PlanStep) -> str:
    selector = tr("Rotary switch: {selector}", selector=f"<b>{escape(step.selector)}</b>")
    return f"<h3>{escape(step.title)}</h3>{selector}"


def settings_html(step: PlanStep, expected: list[tuple[str, str]] = (), element: str = "") -> str:
    """`expected` is what the chosen element states for the settings it decides, by key;
    a setting it does not state is read off the rating plate."""
    stated = dict(expected)
    pairs = [(setting_name(key) or key, stated.get(key) or tr(PLATE))
             for key in step.element_settings]
    items = "".join(f"<li>{escape(k)}: <b>{escape(v)}</b></li>"
                    for k, v in [*pairs, *step.settings])
    title = (tr("Set on the instrument for {element}", element=escape(element))
             if element and stated else tr("Set on the instrument"))
    return f"<b>{title}</b><ul>{items}</ul>" if items else ""


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
