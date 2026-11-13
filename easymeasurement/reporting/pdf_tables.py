# EasyMeasurement - easymeasurement/reporting/pdf_tables.py
# Tables across pages: columns by what they hold, and a remainder named as continued.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from math import sqrt
from xml.sax.saxutils import escape

from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, Paragraph
from reportlab.platypus import Table as PdfTable

from ..l10n import tr
from .nodes import Markup, plain

UNBROKEN = 14  # characters; a value with its unit stays on one line
KEPT_NARROW = "\u202f"  # between a number and its unit: never broken
BREAKING_NARROW = "\u2009"  # after a separator such as "/": a line may break there
_NARROW = 0.6  # a narrow space as a part of a normal one
_BODIES = r"(?:DIN|EN|IEC|ISO|VDE|DGUV|TRBS|ÖVE|ÖNORM)"
# A standard by its bodies and number, as DIN EN 60204-1 or DGUV V3.
STANDARD = re.compile(rf"\b{_BODIES}(?:\s+{_BODIES})*\s+(?:V\s?)?\d[\w.:\-]*")


def kept_standards(text: str) -> str:
    """A standard's name is never broken across lines: its spaces do not break."""
    return STANDARD.sub(lambda found: re.sub(r"\s+", "\xa0", found[0]), text)


def narrow_spaces(markup: str, size: float) -> str:
    """The layout breaks lines at every space and sets each one as wide as a normal space;
    a narrow one is set as a smaller space, kept or breakable as it says. The name of a
    standard stays on one line."""
    small = f"{size * _NARROW:.1f}"
    return (kept_standards(markup).replace(KEPT_NARROW, f'<font size="{small}">\xa0</font>')
            .replace(BREAKING_NARROW, f'<font size="{small}"> </font>'))
WIDEST_TEXT_MM = 70  # a longer text wraps rather than squeeze its neighbours
WIDEST_WORD_MM = 22  # what a column of sentences needs at least, short of room


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
    return Paragraph(narrow_spaces(f"{title} <font size='8'>({marker})</font>", style.fontSize),
                     style)


def column_widths(headers: list[str], rows: list[list[str]], summary: list[list[str]],
                  usable: float, fonts: tuple[str, str], size: float,
                  stretch: int | None = None) -> list[float]:
    """Each column wants its longest text and needs at least its longest word, so numbers
    never wrap; short of room, only the columns of long texts give way. The header and the
    summary rows are set in bold and measured so. A `stretch` column, such as the remarks,
    takes whatever room the others leave, as long as it keeps at least its longest word."""
    regular, bold = fonts
    padding = 12 + 2  # the cell's own padding, left and right, and a little air
    volume: dict[int, float] = {}  # all the text of a column, laid end to end

    def measure(index: int) -> tuple[float, float]:
        cells = [(plain(headers[index]), bold)] + [(plain(row[index]), regular) for row in rows] + [
            (plain(row[index]), bold) for row in summary]
        texts = [(line, font) for text, font in cells for line in text.split("\n")]
        widths = [stringWidth(text, font, size) for text, font in texts]
        volume[index] = sum(widths)
        whole = max(widths)
        word = max(stringWidth(part, font, size) for text, font in texts
                   for part in ([text] if len(text) <= UNBROKEN else text.split() or [""]))
        if whole > WIDEST_WORD_MM * mm * 2:  # a column of sentences may break a long word
            sentences.add(index)
            word = min(word, WIDEST_WORD_MM * mm)
        return min(whole, WIDEST_TEXT_MM * mm) + padding, word + padding

    sentences: set[int] = set()
    wants = {i: measure(i) for i in range(len(headers))}
    room = usable
    wanted = sum(want for want, _ in wants.values())
    if stretch is not None:
        others = wanted - wants[stretch][0]
        if room - others >= wants[stretch][1]:
            share = {i: want for i, (want, _) in wants.items()}
            share[stretch] = room - others
            return [share[i] for i in range(len(headers))]
    short = sum(want for i, (want, _) in wants.items() if i not in sentences)
    if wanted > room and sentences and room - short >= sum(wants[i][1] for i in sentences):
        # Short of room, figures and words keep their width; sentences share what is left, the
        # more text a column holds the more, so that together they need the fewest lines.
        weight = {i: sqrt(volume[i]) or 1 for i in sentences}
        share = {i: want for i, (want, _) in wants.items() if i not in sentences}
        share.update(_shared_out(room - short, weight, {i: wants[i] for i in sentences}))
    elif wanted <= room:
        share = {i: want * room / wanted for i, (want, _) in wants.items()}
    else:
        give = sum(want - least for want, least in wants.values()) or 1
        factor = min((wanted - room) / give, 1)
        share = {i: want - (want - least) * factor for i, (want, least) in wants.items()}
    return [share[i] for i in range(len(headers))]


def _shared_out(room: float, weight: dict[int, float], wants: dict[int, tuple]) -> dict[int, float]:
    """`room` shared by weight; a column never gets more than it wants or less than its longest
    word, and what one gives up goes to the others."""
    share: dict[int, float] = {}
    open_ = dict(weight)
    for _ in range(len(weight)):  # each round settles at least one column or ends
        total = sum(open_.values())
        left = room - sum(share.values())
        settled = {}
        for i, w in open_.items():
            want, least = wants[i]
            fair = left * w / total
            if fair > want or fair < least:
                settled[i] = min(max(fair, least), want)
        if not settled:
            share.update({i: left * w / total for i, w in open_.items()})
            return share
        share.update(settled)
        for i in settled:
            del open_[i]
        if not open_:
            return share
    return share
