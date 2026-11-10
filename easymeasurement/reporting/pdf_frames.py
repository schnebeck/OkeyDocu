# EasyMeasurement - easymeasurement/reporting/pdf_frames.py
# The framed parts of a report: the letterhead at the top and the signature at the end.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.graphics.barcode.qr import QrCodeWidget
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, Paragraph
from reportlab.platypus import Table as PdfTable
from reportlab.platypus import TableStyle

from .language import tr
from .nodes import Letterhead, SignatureLine
from .pdf_parts import _signature_image

QR_MM = 24
GAP_MM = 12  # between two lines to sign
UNBROKEN = 14  # characters; a value with its unit stays on one line
WIDEST_TEXT_MM = 70  # a longer text wraps rather than squeeze its neighbours
_INK = colors.HexColor("#1f2933")
_RULE = colors.HexColor("#c8ced6")
_MUTED = colors.HexColor("#5f6b7a")
_PASSED = colors.HexColor("#1e7b45")
_FAILED = colors.HexColor("#a4262c")


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
    marker = escape(tr("Fortsetzung"))
    return Paragraph(f"{escape(heading)} <font size='8'>({marker})</font>", style)


def _qr(code: str, size: float) -> Drawing:
    widget = QrCodeWidget(code, barBorder=0, barFillColor=_INK, barStrokeColor=_INK)
    left, bottom, right, top = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (right - left), 0, 0, size / (top - bottom),
                                             0, 0])
    drawing.add(widget)
    return drawing


def _lines(lines: list[str], style: ParagraphStyle) -> Paragraph:
    return Paragraph("<br/>".join(escape(line) for line in lines), style)


def letterhead(node: Letterhead, usable: float, body: ParagraphStyle,
               bold: str) -> list[PdfTable]:
    """Code and title side by side, below them who ordered the test and who carried it out."""
    title = ParagraphStyle("lh-title", parent=body, fontName=bold, fontSize=16, leading=20)
    label = ParagraphStyle("lh-label", parent=body, fontName=bold, fontSize=7.5, leading=10,
                           textColor=_MUTED)
    words = [Paragraph(escape(node.title), title), _lines(node.lines, body)]
    if node.code:
        head = PdfTable([[_qr(node.code, QR_MM * mm), words]],
                        colWidths=[(QR_MM + 5) * mm, usable - (QR_MM + 5) * mm])
    else:
        head = PdfTable([[words]], colWidths=[usable])
    head.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    half = usable / 2
    parties = PdfTable(
        [[Paragraph(escape(tr("Auftraggeber")).upper(), label),
          Paragraph(escape(tr("Auftragnehmer")).upper(), label)],
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
    together with it."""
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
        line.append(_signature_image(node.image, width) if last and node.image else "")
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


def column_widths(headers: list[str], rows: list[list[str]], summary: list[list[str]],
                  usable: float, fonts: tuple[str, str], size: float) -> list[float]:
    """Each column wants its longest text and needs at least its longest word, so numbers
    never wrap; short of room, only the columns of long texts give way. The header and the
    summary rows are set in bold and measured so."""
    regular, bold = fonts
    padding = 12  # the cell's own padding, left and right

    def measure(index: int) -> tuple[float, float]:
        texts = [(headers[index], bold)] + [(row[index], regular) for row in rows] + [
            (row[index], bold) for row in summary]
        whole = max(stringWidth(text, font, size) for text, font in texts)
        word = max(stringWidth(part, font, size) for text, font in texts
                   for part in ([text] if len(text) <= UNBROKEN else text.split() or [""]))
        return min(whole, WIDEST_TEXT_MM * mm) + padding, word + padding

    wants = {i: measure(i) for i in range(len(headers))}
    room = usable
    wanted = sum(want for want, _ in wants.values())
    if wanted <= room:
        share = {i: want * room / wanted for i, (want, _) in wants.items()}
    else:
        give = sum(want - least for want, least in wants.values()) or 1
        factor = min((wanted - room) / give, 1)
        share = {i: want - (want - least) * factor for i, (want, least) in wants.items()}
    return [share[i] for i in range(len(headers))]
