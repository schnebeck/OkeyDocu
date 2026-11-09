# EasyMeasurement - easymeasurement/reporting/pdf_parts.py
# Building blocks of the PDF: fonts, numbered pages, logos and images.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image as PilImage
from PIL import ImageOps
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Image

from .language import tr
from .logo import MARGIN_MM, PAGE_HEIGHT_MM, logo_ratio
from .nodes import Logo

_FONT_DIRS = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF")
_MAX_PHOTO_PIXELS = 1400
_SIGNATURE_HEIGHT = 15 * mm


def _register_fonts() -> tuple[str, str]:
    """The reports need Ω, Δ and ², which reportlab's built-in fonts lack."""
    for folder in _FONT_DIRS:
        regular, bold = Path(folder, "DejaVuSans.ttf"), Path(folder, "DejaVuSans-Bold.ttf")
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("Report", str(regular)))
            pdfmetrics.registerFont(TTFont("Report-Bold", str(bold)))
            return "Report", "Report-Bold"
    raise RuntimeError("Schrift DejaVu Sans fehlt (Paket fonts-dejavu-core).")


class _NumberedCanvas(pdf_canvas.Canvas):
    """Holds pages back so the footer can say "page x of y"."""

    footer = ""
    font = "Helvetica"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            self.setFont(self.font, 7.5)
            self.setFillColor(colors.HexColor("#5b6670"))
            self.drawString(18 * mm, 10 * mm, self.footer)
            self.drawRightString(A4[0] - 18 * mm, 10 * mm, tr("Seite {page} von {total}").format(
                page=self._pageNumber, total=total))
            super().showPage()
        super().save()


def _draw_logos(canvas, logos: list[Logo]) -> None:
    for logo in logos:
        height = logo.width_mm * logo_ratio(logo.data)
        canvas.drawImage(
            ImageReader(io.BytesIO(logo.data)),
            logo.x_mm * mm,
            (PAGE_HEIGHT_MM - logo.y_mm - height) * mm,
            logo.width_mm * mm,
            height * mm,
            mask="auto",
        )


def _reserved_space(logos: list[Logo]) -> tuple[float, float, float]:
    """Room to keep free, in mm: top of every page, top of page one, bottom of every page.

    Only logos at the page edges push the text. One in the middle of a page is
    a deliberate overlay, for example a watermark.
    """
    every_top = first_top = bottom = 0.0
    for logo in logos:
        if not logo.reserve:
            continue
        height = logo.width_mm * logo_ratio(logo.data)
        end = logo.y_mm + height
        if logo.y_mm < PAGE_HEIGHT_MM / 3:
            needed = max(0.0, end + 3 - MARGIN_MM)
            if logo.every_page:
                every_top = max(every_top, needed)
            else:
                first_top = max(first_top, needed)
        elif end > PAGE_HEIGHT_MM * 2 / 3:
            bottom = max(bottom, PAGE_HEIGHT_MM - logo.y_mm + 3 - MARGIN_MM)
    return every_top, first_top, bottom


def _signature_image(data: bytes, width: float) -> Image:
    """As large as the space above the line allows, without distorting it."""
    with PilImage.open(io.BytesIO(data)) as source:
        ratio = source.width / source.height
    height = min(_SIGNATURE_HEIGHT, width / ratio)
    return Image(io.BytesIO(data), width=height * ratio, height=height, hAlign="LEFT")


def _photo(path: Path, width: float) -> Image | None:
    try:
        with PilImage.open(path) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
    except OSError:
        return None
    image.thumbnail((_MAX_PHOTO_PIXELS, _MAX_PHOTO_PIXELS))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=82)
    buffer.seek(0)
    return Image(buffer, width=width, height=width * image.height / image.width)
