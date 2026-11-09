# EasyMeasurement - easymeasurement/ui/step_text.py
# How the setup of a measuring step reads on screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from ..campaign.plan import PlanStep


def title_html(step: PlanStep) -> str:
    return f"<h3>{escape(step.title)}</h3>Drehschalter: <b>{escape(step.selector)}</b>"


def settings_html(step: PlanStep) -> str:
    items = "".join(f"<li>{escape(k)}: <b>{escape(v)}</b></li>" for k, v in step.settings)
    return f"<b>Am Gerät einstellen</b><ul>{items}</ul>" if items else ""


def warnings_html(step: PlanStep) -> str:
    items = "".join(f"<li>{escape(text)}</li>" for text in step.warnings)
    return f"<span style='color:#b03a2e'><b>Achtung</b><ul>{items}</ul></span>" if items else ""


def instructions_html(step: PlanStep) -> str:
    items = "".join(f"<li>{escape(text)}</li>" for text in step.instructions)
    dut = f"<b>Prüfling</b><br>{escape(step.dut)}<br><br>" if step.dut else ""
    return f"{dut}<b>Vorgehen</b><ol>{items}</ol>" if items else dut


def source_html(step: PlanStep) -> str:
    return f"<small>Quelle: {escape(step.source)}</small>" if step.source else ""
