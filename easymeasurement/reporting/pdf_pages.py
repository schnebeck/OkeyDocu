# EasyMeasurement - easymeasurement/reporting/pdf_pages.py
# What every page carries outside the text: a short head on the pages after the first, a
# note of the program on the first, and the logos.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Callable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth

from ..l10n import N_, tr
from .nodes import Letterhead, Node
from .pdf_parts import _draw_logos

CREDIT = N_("Report created with EasyMeasurement")
_MUTED = colors.HexColor("#5b6670")
_RULE = colors.HexColor("#c8ced6")
_HEAD_GAP = 5 * mm  # between the head's rule and the text below it
_EDGE = 18 * mm + 6  # where the text of a page starts, inside the frame's own padding
_HEAD_SIZE = 7.5
_HEAD_SPACE = 4 * mm  # between the two halves of the head
ELLIPSIS = "…"


def running_head(nodes: list[Node]) -> tuple[list[str], str]:
    """Title, what was tested and the occasion on the left, the day on the right, as the
    letterhead of the first page says them."""
    head = next((node for node in nodes if isinstance(node, Letterhead)), None)
    if head is None:
        return [], ""
    left = [part for part in (head.title, *head.lines[:-1]) if part]
    return left, head.lines[-1] if len(head.lines) > 1 else ""


def _cut(text: str, font: str, width: float) -> str:
    """The text, or as much of it as fits with an ellipsis after it."""
    if stringWidth(text, font, _HEAD_SIZE) <= width:
        return text
    while text and stringWidth(text + ELLIPSIS, font, _HEAD_SIZE) > width:
        text = text[:-1]
    return text.rstrip(" ·") + ELLIPSIS if text else ""


def fitted_head(parts: list[str], right: str, font: str) -> str:
    """The left half of the head in the room the right half leaves. The title, often a long
    test basis, is shortened first; what was tested and when stays whole while it can."""
    room = A4[0] - 2 * _EDGE - stringWidth(right, font, _HEAD_SIZE) - _HEAD_SPACE
    whole = " · ".join(parts)
    if stringWidth(whole, font, _HEAD_SIZE) <= room or len(parts) < 2:
        return _cut(whole, font, room)
    rest = " · " + " · ".join(parts[1:])
    title_room = room - stringWidth(rest, font, _HEAD_SIZE)
    if title_room < room / 4:  # too little left for the title to say anything
        return _cut(" · ".join(parts[1:]), font, room)
    return _cut(parts[0], font, title_room) + rest


def _head(canvas, font: str, left: str, right: str, top: float) -> None:
    """One line and a rule right above the text, so every page shows what it belongs to."""
    if not (left or right):
        return
    line = top + _HEAD_GAP
    canvas.setFont(font, _HEAD_SIZE)
    canvas.setFillColor(_MUTED)
    canvas.drawString(_EDGE, line + 3, left)
    canvas.drawRightString(A4[0] - _EDGE, line + 3, right)
    canvas.setStrokeColor(_RULE)
    canvas.setLineWidth(0.6)
    canvas.line(_EDGE, line, A4[0] - _EDGE, line)


def _credit(canvas, font: str) -> None:
    """Upright along the left edge, at the foot of the first page."""
    canvas.saveState()
    canvas.setFont(font, 6.5)
    canvas.setFillColor(_MUTED)
    canvas.translate(_EDGE / 2, 22 * mm)
    canvas.rotate(90)
    canvas.drawString(0, 0, tr(CREDIT))
    canvas.restoreState()


def page_painters(nodes: list[Node], logos: list, budget, font: str,
                  top: float) -> tuple[Callable, Callable]:
    """What the first page and the later pages draw before their text; `top` is where the
    text of a page begins, from the bottom of the sheet."""
    parts, right = running_head(nodes)
    left = fitted_head(parts, right, font)
    every_page = [logo for logo in logos if logo.every_page]

    def first_page(canvas, _) -> None:
        budget.new_page()
        _draw_logos(canvas, logos)
        _credit(canvas, font)

    def later_page(canvas, _) -> None:
        budget.new_page()
        _draw_logos(canvas, every_page)
        _head(canvas, font, left, right, top)

    return first_page, later_page
