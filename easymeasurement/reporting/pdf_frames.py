# EasyMeasurement - easymeasurement/reporting/pdf_frames.py
# The framed parts of a report: the letterhead at the top and the signature at the end.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
from xml.sax.saxutils import escape

from PIL import Image as PilImage

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph
from reportlab.platypus import Table as PdfTable
from reportlab.platypus import TableStyle

from ..l10n import tr
from .nodes import Letterhead, SignatureLine
from .logo import trimmed
from .pdf_parts import _signature_image

QR_MM = 24
LOGO_BOX_MM = (55, 24)  # the most the firm's logo takes beside the title
GAP_MM = 12  # between two lines to sign
_INK = colors.HexColor("#1f2933")
_RULE = colors.HexColor("#c8ced6")
_MUTED = colors.HexColor("#5f6b7a")
_PASSED = colors.HexColor("#1e7b45")
_FAILED = colors.HexColor("#a4262c")


def _qr(code: str, size: float) -> Drawing:
    widget = QrCodeWidget(code, barBorder=0, barFillColor=_INK, barStrokeColor=_INK)
    left, bottom, right, top = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (right - left), 0, 0, size / (top - bottom),
                                             0, 0])
    drawing.add(widget)
    return drawing


def _logo(data: bytes) -> Image:
    """As large as the box beside the title allows, keeping its proportions; its empty
    border cut off, so it stands flush with the top and the right of the printed area."""
    data = trimmed(data)
    with PilImage.open(io.BytesIO(data)) as source:
        ratio = source.width / source.height
    width, height = LOGO_BOX_MM[0] * mm, LOGO_BOX_MM[1] * mm
    if width / ratio > height:
        width = height * ratio
    return Image(io.BytesIO(data), width=width, height=width / ratio, hAlign="RIGHT")


def _lines(lines: list[str], style: ParagraphStyle) -> Paragraph:
    return Paragraph("<br/>".join(escape(line) for line in lines), style)


def letterhead(node: Letterhead, usable: float, body: ParagraphStyle,
               bold: str) -> list[PdfTable]:
    """Code and title side by side, below them who ordered the test and who carried it out."""
    title = ParagraphStyle("lh-title", parent=body, fontName=bold, fontSize=16, leading=20)
    label = ParagraphStyle("lh-label", parent=body, fontName=bold, fontSize=7.5, leading=10,
                           textColor=_MUTED)
    cells, widths = [], []
    if node.code:
        cells.append(_qr(node.code, QR_MM * mm))
        widths.append((QR_MM + 5) * mm)
    cells.append([Paragraph(escape(node.title), title), _lines(node.lines, body)])
    widths.append(usable - sum(widths) - (LOGO_BOX_MM[0] * mm if node.logo else 0))
    if node.logo:
        cells.append(_logo(node.logo))
        widths.append(LOGO_BOX_MM[0] * mm)
    head = PdfTable([cells], colWidths=widths)
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (-1, 0), (-1, 0),
                              "RIGHT" if node.logo else "LEFT"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (-1, 0), (-1, 0), 0),
                              ("TOPPADDING", (-1, 0), (-1, 0), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    half = usable / 2
    parties = PdfTable(
        [[Paragraph(escape(tr("Client")).upper(), label),
          Paragraph(escape(tr("Contractor")).upper(), label)],
         [_lines(node.client, body), _lines(node.contractor, body)]],
        colWidths=[half, half])
    parties.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, _RULE),
        ("LINEBEFORE", (1, 0), (1, -1), 0.6, _RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 8),
    ]))
    return [head, parties]


def signature(node: SignatureLine, usable: float, cell: ParagraphStyle, body: ParagraphStyle,
              bold: str) -> PdfTable:
    """A line to sign over each label, with a gap between the lines; with a result, framed
    together with it. What is known already, such as place, date and name, is written on the
    lines; the stored signature takes the place of the name."""
    framed = bool(node.result)
    count = len(node.labels)
    room = usable - (14 * mm if framed else 0) - GAP_MM * mm * (count - 1)
    width = room / count
    widths, line, labels = [], [], []
    for index, label in enumerate(node.labels):
        if index:
            widths.append(GAP_MM * mm)
            line.append("")
            labels.append("")
        widths.append(width)
        last = index == count - 1
        fill = node.fills[index] if index < len(node.fills) else ""
        if last and node.image:  # a signature drawn by hand stands in for the name
            line.append(_signature_image(node.image, width))
        else:
            line.append(Paragraph(escape(fill), body) if fill else "")
        labels.append(Paragraph(escape(label), cell))
    rows = [line, labels]
    style = [("VALIGN", (0, 0), (-1, 0), "BOTTOM"), ("BOTTOMPADDING", (0, 0), (-1, 0), 1),
             ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0)]
    style += [("LINEBELOW", (column, 0), (column, 0), 0.6, _INK)
              for column in range(0, len(widths), 2)]
    heights = [16 * mm, None]
    if framed:
        colour = {"passed": _PASSED, "failed": _FAILED}.get(node.tone, _INK)
        verdict = ParagraphStyle("verdict", parent=body, fontName=bold, fontSize=11, leading=14,
                                 textColor=colour)
        rows.insert(0, [Paragraph(escape(node.result), verdict)] + [""] * (len(widths) - 1))
        heights.insert(0, None)
        style = [(command, (start[0], start[1] + 1), (end[0], end[1] + 1), *rest)
                 for command, start, end, *rest in style]
        style += [("SPAN", (0, 0), (-1, 0)), ("TOPPADDING", (0, 0), (-1, 0), 2)]
        inner = PdfTable(rows, colWidths=widths, rowHeights=heights)
        inner.setStyle(TableStyle(style))
        frame = PdfTable([[inner]], colWidths=[usable])
        frame.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, _RULE),
                                   ("LEFTPADDING", (0, 0), (-1, -1), 7 * mm),
                                   ("RIGHTPADDING", (0, 0), (-1, -1), 7 * mm),
                                   ("TOPPADDING", (0, 0), (-1, -1), 8),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        return frame
    table = PdfTable(rows, colWidths=widths, rowHeights=heights)
    table.setStyle(TableStyle(style))
    return table
