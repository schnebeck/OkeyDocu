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
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)
from reportlab.platypus import Table as PdfTable
from reportlab.platypus import TableStyle

from .language import tr
from .logo import MARGIN_MM
from .nodes import Fields, Heading, Logo, Node, Notice, Photos, SignatureLine, Table
from .nodes import Paragraph as TextNode
from .pdf_parts import (
    _draw_logos,
    _NumberedCanvas,
    _photo,
    _register_fonts,
    _reserved_space,
    _signature_image,
)

_INK = colors.HexColor("#1f2933")
_RULE = colors.HexColor("#c8ced6")
_SHADE = colors.HexColor("#eef1f4")
_ALERT = colors.HexColor("#a4262c")


def render_pdf(nodes: list[Node], target: Path | io.BytesIO, footer: str = "") -> None:
    regular, bold = _register_fonts()
    body = ParagraphStyle("body", fontName=regular, fontSize=9.5, leading=13, textColor=_INK,
                          alignment=TA_LEFT)
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
        count = len(node.headers)
        fixed = {0: 14 * mm, 1: 26 * mm, count - 1: 32 * mm}
        rest = (usable - sum(fixed.values())) / max(count - 3, 1)
        widths = [fixed.get(i, rest) for i in range(count)]
        result = PdfTable(rows, colWidths=widths, repeatRows=1)
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
        for path, caption in node.items:
            image = _photo(path, width)
            if image:
                images.append([image, text(caption, cell)])
        if not images:
            return None
        rows = [images[i : i + 2] for i in range(0, len(images), 2)]
        if len(rows[-1]) == 1:
            rows[-1].append("")
        grid = PdfTable(rows, colWidths=[width + 3 * mm] * 2)
        grid.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0),
                                  ("VALIGN", (0, 0), (-1, -1), "TOP")]))
        return grid

    def signature(node: SignatureLine) -> PdfTable:
        width = usable / len(node.labels)
        line: list = [""] * len(node.labels)
        if node.image:
            line[-1] = _signature_image(node.image, width)
        rows = [line, [text(label, cell) for label in node.labels]]
        table_ = PdfTable(rows, colWidths=[width] * len(node.labels), rowHeights=[16 * mm, None])
        table_.setStyle(TableStyle([
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, _INK),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ]))
        return table_

    logos = [node for node in nodes if isinstance(node, Logo)]
    every_top, first_top, bottom = _reserved_space(logos)
    story = []
    if first_top > every_top:
        story.append(Spacer(1, (first_top - every_top) * mm))
    pending_heading = None
    for node in nodes:
        if isinstance(node, Heading):
            if pending_heading is not None:
                story.append(pending_heading)
            pending_heading = text(node.text, heading[min(node.level, 3)])
            continue
        if isinstance(node, TextNode):
            flowable = text(node.text)
        elif isinstance(node, Notice):
            flowable = text(node.text, alert)
        elif isinstance(node, Fields):
            flowable = fields(node)
        elif isinstance(node, Table):
            flowable = table(node)
        elif isinstance(node, Photos):
            flowable = photos(node)
        elif isinstance(node, SignatureLine):
            flowable = signature(node)
        else:
            continue
        if flowable is None:
            continue
        # A heading must not be stranded at the bottom of a page.
        if pending_heading is not None and not isinstance(node, Table):
            story.append(KeepTogether([pending_heading, flowable]))
        else:
            if pending_heading is not None:
                story.append(pending_heading)
            story.append(flowable)
        pending_heading = None
        story.append(Spacer(1, 4))
    if pending_heading is not None:
        story.append(pending_heading)

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
