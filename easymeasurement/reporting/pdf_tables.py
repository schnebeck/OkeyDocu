# EasyMeasurement - easymeasurement/reporting/pdf_tables.py
# Tables across pages: columns by what they hold, and a remainder named as continued.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, Paragraph
from reportlab.platypus import Table as PdfTable

from ..l10n import tr
from .nodes import Markup, plain

UNBROKEN = 14  # characters; a value with its unit stays on one line
WIDEST_TEXT_MM = 70  # a longer text wraps rather than squeeze its neighbours


class ContinuedTable(PdfTable):
    """A table that, broken across pages, starts again under its caption marked as continued.

    The header rows repeat by themselves. The caption goes before the remainder behind a
    page break, so it never stays alone at the foot of the page just filled.
    """

    caption: Paragraph | None = None

    def split(self, availWidth, availHeight):
        parts = super().split(availWidth, availHeight)
        if len(parts) != 2 or self.caption is None:
            return parts
        rest = parts[1]
        rest.caption = self.caption
        # Whatever room the first part leaves is too small for the next row, or there would
        # have been no split: the break asks for one point more than that room.
        left = availHeight - parts[0].wrap(availWidth, availHeight)[1]
        return [parts[0], CondPageBreak(left + 1), self.caption, rest]


def caption_of(heading: str, style: ParagraphStyle) -> Paragraph:
    marker = escape(tr("continued"))
    title = heading if isinstance(heading, Markup) else escape(heading)
    return Paragraph(f"{title} <font size='8'>({marker})</font>", style)


def column_widths(headers: list[str], rows: list[list[str]], summary: list[list[str]],
                  usable: float, fonts: tuple[str, str], size: float,
                  stretch: int | None = None) -> list[float]:
    """Each column wants its longest text and needs at least its longest word, so numbers
    never wrap; short of room, only the columns of long texts give way. The header and the
    summary rows are set in bold and measured so. A `stretch` column, such as the remarks,
    takes whatever room the others leave, as long as it keeps at least its longest word."""
    regular, bold = fonts
    padding = 12 + 2  # the cell's own padding, left and right, and a little air

    def measure(index: int) -> tuple[float, float]:
        texts = [(plain(headers[index]), bold)] + [(plain(row[index]), regular) for row in rows] + [
            (plain(row[index]), bold) for row in summary]
        whole = max(stringWidth(text, font, size) for text, font in texts)
        word = max(stringWidth(part, font, size) for text, font in texts
                   for part in ([text] if len(text) <= UNBROKEN else text.split() or [""]))
        return min(whole, WIDEST_TEXT_MM * mm) + padding, word + padding

    wants = {i: measure(i) for i in range(len(headers))}
    room = usable
    wanted = sum(want for want, _ in wants.values())
    if stretch is not None:
        others = wanted - wants[stretch][0]
        if room - others >= wants[stretch][1]:
            share = {i: want for i, (want, _) in wants.items()}
            share[stretch] = room - others
            return [share[i] for i in range(len(headers))]
    if wanted <= room:
        share = {i: want * room / wanted for i, (want, _) in wants.items()}
    else:
        give = sum(want - least for want, least in wants.values()) or 1
        factor = min((wanted - room) / give, 1)
        share = {i: want - (want - least) * factor for i, (want, least) in wants.items()}
    return [share[i] for i in range(len(headers))]
