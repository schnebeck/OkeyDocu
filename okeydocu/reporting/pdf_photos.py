# OkeyDocu - okeydocu/reporting/pdf_photos.py
# Photos in the PDF: three side by side, two rows a page, beside the rows that name them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A table whose rows refer to photos is set together with them, as text and its footnotes
are: a page takes as many rows as fit with the photos those rows name, and the photos stand
right below them. A page never holds more than two rows of photos; a row of photos that
would be the third waits for the next page. `PageBudget` counts the rows of the current
page; the document resets it whenever a page begins."""
from __future__ import annotations

from typing import Callable
from xml.sax.saxutils import escape

from reportlab.lib.units import mm
from reportlab.platypus import CondPageBreak, Flowable, Paragraph, Spacer
from reportlab.platypus import Table as PdfTable
from reportlab.platypus import TableStyle

from .nodes import Markup
from .pdf_parts import _photos

PER_ROW = 3
ROWS_PER_PAGE = 2
GAP = 3 * mm
_BEFORE = 4  # points between a table and its photos
_FRESH = 0.9  # share of a page's height above which a page counts as unused
KEPT = 2  # rows a table keeps together where it breaks


class PageBudget:
    def __init__(self):
        self.rows_left = ROWS_PER_PAGE

    def new_page(self) -> None:
        self.rows_left = ROWS_PER_PAGE


class PhotoRow(Flowable):
    """Up to three photos with their captions, never split."""

    def __init__(self, cells: list, width: float, budget: PageBudget):
        super().__init__()
        column = width / PER_ROW
        padded = cells + [""] * (PER_ROW - len(cells))
        self.grid = PdfTable([padded], colWidths=[column] * PER_ROW)
        self.grid.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), GAP),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        self.budget = budget

    def wrap(self, availWidth, availHeight):
        self.width, self.height = self.grid.wrap(availWidth, availHeight)
        if self.budget.rows_left <= 0:  # the page has its photos; this row takes the next one
            return self.width, max(self.height, availHeight + 1)
        return self.width, self.height

    def split(self, availWidth, availHeight):
        return []

    def draw(self):
        self.budget.rows_left -= 1
        self.grid.drawOn(self.canv, 0, 0)


def photo_rows(cells: list, width: float, budget: PageBudget) -> list[PhotoRow]:
    return [PhotoRow(cells[start:start + PER_ROW], width, budget)
            for start in range(0, len(cells), PER_ROW)]


class Footnoted(Flowable):
    """Rows of a table and the photos they refer to; `counts` says how many photos each
    row brings, in the order of `cells`. `build(rows, last)` makes the table of some rows,
    with its summary only where `last` is true."""

    def __init__(self, build: Callable, rows: list, counts: list[int], cells: list,
                 width: float, budget: PageBudget, page_height: float, caption=None,
                 lead: list | None = None):
        super().__init__()
        self.build, self.rows, self.counts, self.cells = build, rows, counts, cells
        self.full_width, self.budget, self.page_height = width, budget, page_height
        self.caption = caption
        self.lead = lead or []  # headings and what stands above the table, kept with its start
        self._parts: list[Flowable] = []

    def _taken(self, rows: int) -> int:
        return sum(self.counts[:rows])

    def parts(self, rows: int) -> list[Flowable]:
        table = self.build(self.rows[:rows], rows == len(self.rows))
        photos = photo_rows(self.cells[:self._taken(rows)], self.full_width, self.budget)
        return [*self.lead, table, *([Spacer(1, _BEFORE)] if photos else []), *photos]

    def _height(self, part: Flowable, width: float, first: bool) -> float:
        """With the room a heading keeps around itself, as the frame would give it."""
        inner = part.grid if isinstance(part, PhotoRow) else part
        above = 0 if first else part.getSpaceBefore()
        return above + inner.wrap(width, self.page_height)[1] + part.getSpaceAfter()

    def _measure(self, parts: list[Flowable], width: float,
                 loose: bool = False) -> tuple[float, int]:
        """Drawn whole, the first part's room above is this flowable's own; handed to the
        frame one by one (`loose`), the frame gives it that room as to any other."""
        height = sum(self._height(part, width, index == 0 and not loose)
                     for index, part in enumerate(parts))
        return height, sum(isinstance(part, PhotoRow) for part in parts)

    def _fits(self, parts: list[Flowable], width: float, height: float) -> bool:
        needed, photos = self._measure(parts, width, loose=True)
        return needed <= height and photos <= self.budget.rows_left

    def wrap(self, availWidth, availHeight):
        self._parts = self.parts(len(self.rows))
        self.width = availWidth
        self.height, photos = self._measure(self._parts, availWidth)
        if photos > self.budget.rows_left:
            return availWidth, max(self.height, availHeight + 1)
        return availWidth, self.height

    def split(self, availWidth, availHeight):
        best, low, high = 0, 1, len(self.rows)
        while low <= high:  # more rows never need less room, so halving finds the most
            middle = (low + high) // 2
            if self._fits(self.parts(middle), availWidth, availHeight):
                best, low = middle, middle + 1
            else:
                high = middle - 1
        if 0 < len(self.rows) - best < KEPT and best > KEPT:
            best -= 1  # no row stands alone at the head of the next page
        if best < min(KEPT, len(self.rows)):  # nor alone at the foot of this one
            best = 0
        if best == 0:
            fresh = availHeight >= self.page_height * _FRESH
            if not (fresh and self.budget.rows_left == ROWS_PER_PAGE):
                return []
            best = 1  # a row with more photos than a page holds: they follow on their own
        parts = self.parts(best)
        if best == len(self.rows):
            return parts
        rest = Footnoted(self.build, self.rows[best:], self.counts[best:],
                         self.cells[self._taken(best):], self.full_width, self.budget,
                         self.page_height, self.caption)
        # The rest never fits beside what this page took: it starts the next page, its caption
        # with it. A page left almost whole, as after a forced row, is not left empty.
        tail = [CondPageBreak(self.page_height * _FRESH)]
        return parts + tail + ([self.caption] if self.caption is not None else []) + [rest]

    def draw(self):
        """Each part where the frame would have set it on its own, aligned as it asks."""
        top = self.height
        for index, part in enumerate(self._parts):
            top -= 0 if index == 0 else part.getSpaceBefore()
            width, height = part.wrap(self.width, self.page_height)
            top -= height
            align = str(getattr(part, "hAlign", "LEFT")).upper()
            left = {"CENTER": (self.width - width) / 2, "CENTRE": (self.width - width) / 2,
                    "RIGHT": self.width - width}.get(align, 0)
            part.drawOn(self.canv, left, top)
            top -= part.getSpaceAfter()


def photo_cells(items: list[tuple], width: float, style, bold: str, alert: str) -> list:
    """Photo and caption for each item `(path, caption, marks, role, notes)`; the last three
    may be missing. A caption given as markup keeps it and the notes follow it line by line;
    a plain one has its lines and its role as the lead, in red for a defect. A photo fits a
    square as wide as its column."""
    box = width / PER_ROW - GAP
    cells = []
    for (path, caption, *more), image in zip(items, _photos(items, box)):
        if image is None:
            continue
        if image.drawHeight > box:
            image.drawWidth, image.drawHeight = image.drawWidth * box / image.drawHeight, box
        role = more[1] if len(more) > 1 else ""
        if isinstance(caption, Markup):
            notes = more[2] if len(more) > 2 else []
            lead = f'<font color="{alert}">{caption}</font>' if role == "defect" else caption
            cells.append([image, Paragraph("<br/>".join([lead, *map(escape, notes)]), style)])
            continue
        lines = "<br/>".join(escape(part) for part in caption.split("\n"))
        if role:
            lead, _, rest = lines.partition(": ")
            lead = f'<font name="{bold}">{lead}:</font>'
            if role == "defect":
                lead = f'<font color="{alert}">{lead}</font>'
            lines = f"{lead} {rest}"
        cells.append([image, Paragraph(lines, style)])
    return cells
