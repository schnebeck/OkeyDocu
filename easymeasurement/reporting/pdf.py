# EasyMeasurement - easymeasurement/reporting/pdf.py
# Renders resolved document nodes to PDF.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from reportlab.platypus import Table as PdfTable
from reportlab.platypus import TableStyle

from ..l10n import tr
from .logo import MARGIN_MM
from .nodes import (
    Fields,
    Footnoted,
    Heading,
    Letterhead,
    Logo,
    Markup,
    Node,
    Notice,
    Photos,
    SignatureLine,
    Table,
)
from .nodes import Paragraph as TextNode
from .pdf_frames import letterhead, signature
from .pdf_tables import ContinuedTable, caption_of, column_widths
from .pdf_parts import _draw_logos, _NumberedCanvas, _register_fonts, _reserved_space
from .pdf_photos import Footnoted as FootnotedFlowable
from .pdf_photos import PageBudget, photo_cells, photo_rows

_INK = colors.HexColor("#1f2933")
_RULE = colors.HexColor("#c8ced6")
_SHADE = colors.HexColor("#eef1f4")
_ALERT = colors.HexColor("#a4262c")
_FRAME_PADDING = 6
_KEEP_TABLE = 22 * mm  # a table's header and its first rows
_KEEP_PHOTOS = 75 * mm  # one row of photos with their captions


def render_pdf(nodes: list[Node], target: Path | io.BytesIO, footer: str = "") -> None:
    regular, bold = _register_fonts()
    # No paragraph leaves a single line at the foot or the head of a page.
    body = ParagraphStyle("body", fontName=regular, fontSize=9.5, leading=13, textColor=_INK,
                          alignment=TA_LEFT, allowWidows=0, allowOrphans=0)
    cell = ParagraphStyle("cell", parent=body, fontSize=8.5, leading=11)
    head_cell = ParagraphStyle("headcell", parent=cell, fontName=bold)
    heading = {
        1: ParagraphStyle("h1", parent=body, fontName=bold, fontSize=18, leading=22, spaceAfter=8),
        2: ParagraphStyle("h2", parent=body, fontName=bold, fontSize=12, leading=15, spaceBefore=12,
                          spaceAfter=5),
        3: ParagraphStyle("h3", parent=body, fontName=bold, fontSize=9.5, leading=12, spaceBefore=6,
                          spaceAfter=3),
    }
    alert = ParagraphStyle("alert", parent=body, fontName=bold, textColor=_ALERT)
    # The frame keeps 6 points on either side; what is as wide as it starts where text does.
    usable = A4[0] - 36 * mm - 2 * _FRAME_PADDING

    budget = PageBudget()
    page_height = A4[1] - 2 * MARGIN_MM * mm

    def text(value: str, style=body) -> Paragraph:
        """Markup as it is; plain text escaped, each of its lines on a line of its own."""
        shown = value if isinstance(value, Markup) else escape(value).replace("\n", "<br/>")
        return Paragraph(shown, style)

    def field_rows(node: Fields) -> list[list[Paragraph]]:
        return [[text(k, head_cell), text(v, cell)] for k, v in node.rows if v.strip()]

    def fields(node: Fields, rows: list | None = None) -> PdfTable:
        rows = field_rows(node) if rows is None else rows
        table = PdfTable(rows, colWidths=[usable * 0.3, usable * 0.7])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, _RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
        ]))
        return table

    def table(node: Table, body: list | None = None, last: bool = True) -> PdfTable:
        rows = [[text(h, head_cell) for h in node.headers]]
        rows += [[text(c, cell) for c in row] for row in node.rows] if body is None else body
        rows += [[text(c, head_cell) for c in row] for row in node.summary] if last else []
        if not hasattr(node, "widths"):  # the same columns on every page the table spans
            node.widths = column_widths(node.headers, node.rows, node.summary, usable,
                                        (regular, bold), cell.fontSize)
        result = ContinuedTable(rows, colWidths=node.widths, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), _SHADE),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, _RULE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]
        if node.summary and last:
            first = len(rows) - len(node.summary)
            style.append(("LINEABOVE", (0, first), (-1, first), 0.8, _INK))
        result.setStyle(TableStyle(style))
        return result

    def cells(items: list[tuple]) -> list:
        return photo_cells(items, usable, cell, bold, f"#{_ALERT.hexval()[2:]}")

    def footnoted(node: Footnoted, caption, lead: list) -> FootnotedFlowable:
        """The photos below the rows that name them; their marks' texts under each photo."""
        items = [(note.path, note.caption, note.marks, note.role, note.notes, note.view)
                 for note in node.photos]
        if isinstance(node.body, Table):
            rows = [[text(c, cell) for c in row] for row in node.body.rows]
            build = lambda part, last: table(node.body, part, last)  # noqa: E731
        else:
            rows = field_rows(node.body)
            build = lambda part, last: fields(node.body, part)  # noqa: E731
            node.refs = [refs for (_, v), refs in zip(node.body.rows, node.refs) if v.strip()]
        counts = [len(refs) for refs in node.refs]
        return FootnotedFlowable(build, rows, counts, cells(items), usable, budget, page_height,
                                 caption, lead)

    logos = [node for node in nodes if isinstance(node, Logo)]
    every_top, first_top, bottom = _reserved_space(logos)
    story = []
    if first_top > every_top:
        story.append(Spacer(1, (first_top - every_top) * mm))
    headings: list = []  # waiting for what they stand over
    title = ""  # the nearest heading, named again where a table goes on over a page
    for index, node in enumerate(nodes):
        if isinstance(node, Heading):
            headings.append(text(node.text, heading[min(node.level, 3)]))
            title = node.text
            continue
        following = nodes[index + 1] if index + 1 < len(nodes) else None
        if isinstance(node, Fields) and isinstance(following, (Table, Footnoted)):
            headings.append(fields(node))  # what a block shares stays with its table
            continue
        if isinstance(node, TextNode):
            flowable = text(node.text)
        elif isinstance(node, Notice):
            flowable = text(node.text, alert)
        elif isinstance(node, Fields):
            flowable = fields(node)
        elif isinstance(node, Table):
            flowable = table(node)
            flowable.caption = caption_of(title, heading[3]) if title else None
        elif isinstance(node, Footnoted):
            story.append(footnoted(node, caption_of(title, heading[3]) if title else None,
                                   headings))
            headings = []
            story.append(Spacer(1, 4))
            continue
        elif isinstance(node, Photos):
            rows = photo_rows(cells(node.items), usable, budget)
            if rows:
                above = sum(item.wrap(usable, A4[1])[1] for item in headings)
                story += [CondPageBreak(_KEEP_PHOTOS + above), *headings, *rows]
                headings = []
            continue
        elif isinstance(node, SignatureLine):
            flowable = signature(node, usable, cell, body, bold)
        elif isinstance(node, Letterhead):
            story.extend(letterhead(node, usable, body, bold))
            story.append(Spacer(1, 10))
            continue
        else:
            continue
        # Headings never stay alone at the foot of a page: they go with what follows, and a
        # long table or a row of photos starts on a new page unless its beginning still fits.
        if isinstance(node, Table):
            above = sum(item.wrap(usable, A4[1])[1] for item in headings)
            story.append(CondPageBreak(_KEEP_TABLE + above))
            story.extend(headings)
            story.append(flowable)
        elif headings:
            story.append(KeepTogether([*headings, flowable]))
        else:
            story.append(flowable)
        headings = []
        story.append(Spacer(1, 4))
    story.extend(headings)

    canvas_class = type("Canvas", (_NumberedCanvas,), {"footer": footer, "font": regular})
    document = SimpleDocTemplate(
        str(target) if isinstance(target, Path) else target, pagesize=A4, leftMargin=18 * mm,
        rightMargin=18 * mm, topMargin=(MARGIN_MM + every_top) * mm,
        bottomMargin=(MARGIN_MM + bottom) * mm, title=tr("Test report"), author="",
        creator="EasyMeasurement",
    )
    every_page = [logo for logo in logos if logo.every_page]

    def first_page(canvas, _) -> None:
        budget.new_page()
        _draw_logos(canvas, logos)

    def later_page(canvas, _) -> None:
        budget.new_page()
        _draw_logos(canvas, every_page)

    document.build(story, onFirstPage=first_page, onLaterPages=later_page,
                   canvasmaker=canvas_class)
