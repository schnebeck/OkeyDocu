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

from .language import tr
from .logo import MARGIN_MM
from .nodes import Fields, Heading, Letterhead, Logo, Node, Notice, Photos, SignatureLine, Table
from .nodes import Paragraph as TextNode
from .pdf_frames import letterhead, signature
from .pdf_tables import ContinuedTable, caption_of, column_widths
from .pdf_parts import (
    _draw_logos,
    _NumberedCanvas,
    _photos,
    _register_fonts,
    _reserved_space,
)

_INK = colors.HexColor("#1f2933")
_RULE = colors.HexColor("#c8ced6")
_SHADE = colors.HexColor("#eef1f4")
_ALERT = colors.HexColor("#a4262c")
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
    usable = A4[0] - 36 * mm

    def text(value: str, style=body) -> Paragraph:
        return Paragraph(escape(value), style)

    def fields(node: Fields) -> PdfTable:
        rows = [[text(k, head_cell), text(v, cell)] for k, v in node.rows if v.strip()]
        table = PdfTable(rows, colWidths=[usable * 0.3, usable * 0.7])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, _RULE),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
            ("LEFTPADDING", (0, 0), (0, -1), 0),
        ]))
        return table

    def table(node: Table) -> PdfTable:
        rows = [[text(h, head_cell) for h in node.headers]]
        rows += [[text(c, cell) for c in row] for row in node.rows]
        rows += [[text(c, head_cell) for c in row] for row in node.summary]
        widths = column_widths(node.headers, node.rows, node.summary, usable, (regular, bold),
                               cell.fontSize)
        result = ContinuedTable(rows, colWidths=widths, repeatRows=1)
        style = [
            ("BACKGROUND", (0, 0), (-1, 0), _SHADE),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, _RULE),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ]
        if node.summary:
            first = len(rows) - len(node.summary)
            style.append(("LINEABOVE", (0, first), (-1, first), 0.8, _INK))
        result.setStyle(TableStyle(style))
        return result

    def photos(node: Photos) -> PdfTable | None:
        width = (usable - 6 * mm) / 2
        images = []
        for (path, caption, *notes), image in zip(node.items, _photos(node.items, width)):
            role = notes[1] if len(notes) > 1 else ""
            if image:
                lines = "<br/>".join(escape(part) for part in caption.split("\n"))
                if role:
                    # The role leads the caption: in red for a defect, in bold for a hint.
                    word, _, rest = lines.partition(": ")
                    lead = f'<font name="{bold}">{word}:</font>'
                    if role == "defect":
                        lead = f'<font color="#{_ALERT.hexval()[2:]}">{lead}</font>'
                    lines = f"{lead} {rest}"
                images.append([image, Paragraph(lines, cell)])
        if not images:
            return None
        rows = [images[i : i + 2] for i in range(0, len(images), 2)]
        if len(rows[-1]) == 1:
            rows[-1].append("")
        grid = PdfTable(rows, colWidths=[width + 3 * mm] * 2)
        grid.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return grid

    logos = [node for node in nodes if isinstance(node, Logo)]
    every_top, first_top, bottom = _reserved_space(logos)
    story = []
    if first_top > every_top:
        story.append(Spacer(1, (first_top - every_top) * mm))
    headings: list = []  # waiting for what they stand over
    title = ""  # the nearest heading, named again where a table goes on over a page
    for node in nodes:
        if isinstance(node, Heading):
            headings.append(text(node.text, heading[min(node.level, 3)]))
            title = node.text
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
        elif isinstance(node, Photos):
            flowable = photos(node)
        elif isinstance(node, SignatureLine):
            flowable = signature(node, usable, cell, body, bold)
        elif isinstance(node, Letterhead):
            story.extend(letterhead(node, usable, body, bold))
            story.append(Spacer(1, 10))
            continue
        else:
            continue
        if flowable is None:
            continue
        # Headings never stay alone at the foot of a page: they go with what follows, and a
        # long table or a row of photos starts on a new page unless its beginning still fits.
        if isinstance(node, (Table, Photos)):
            story.append(CondPageBreak((_KEEP_TABLE if isinstance(node, Table) else _KEEP_PHOTOS)
                                       + 20 * len(headings)))
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
        bottomMargin=(MARGIN_MM + bottom) * mm, title=tr("Prüfprotokoll"), author="",
        creator="EasyMeasurement",
    )
    every_page = [logo for logo in logos if logo.every_page]
    document.build(
        story,
        onFirstPage=lambda canvas, _: _draw_logos(canvas, logos),
        onLaterPages=lambda canvas, _: _draw_logos(canvas, every_page),
        canvasmaker=canvas_class,
    )
