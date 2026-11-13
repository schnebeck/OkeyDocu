# OkeyDocu - okeydocu/reporting/pdf_parts.py
# Building blocks of the PDF: fonts, numbered pages, logos and images.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import io
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image as PilImage
from PIL import ImageDraw, ImageFont
from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.platypus import Flowable, Image

from ..campaign.photo_proxies import QUALITY, make_proxy, reduced
from ..l10n import tr
from .logo import MARGIN_MM, PAGE_HEIGHT_MM, logo_ratio
from .nodes import Logo

_FONT_DIRS = ("/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF")
# Pictures and page streams go into the file as compressed bytes, not spelt out in ASCII85,
# which makes them a quarter larger and is encoded slowly in Python.
rl_config.useA85 = 0
_MARK_RGB = (231, 76, 60)  # the red of the marks on screen
_SIGNATURE_HEIGHT = 15 * mm


def _register_fonts() -> tuple[str, str]:
    """The reports need Ω, Δ and ², which reportlab's built-in fonts lack. Symbols of
    quantities are set in italic; without the oblique faces they stay upright."""
    for folder in _FONT_DIRS:
        regular, bold = Path(folder, "DejaVuSans.ttf"), Path(folder, "DejaVuSans-Bold.ttf")
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("Report", str(regular)))
            pdfmetrics.registerFont(TTFont("Report-Bold", str(bold)))
            faces = {"italic": "Report", "boldItalic": "Report-Bold"}
            for face, name, file in (("italic", "Report-Italic", "DejaVuSans-Oblique.ttf"),
                                     ("boldItalic", "Report-BoldItalic",
                                      "DejaVuSans-BoldOblique.ttf")):
                if Path(folder, file).exists():
                    pdfmetrics.registerFont(TTFont(name, str(Path(folder, file))))
                    faces[face] = name
            registerFontFamily("Report", normal="Report", bold="Report-Bold", **faces)
            return "Report", "Report-Bold"
    raise RuntimeError(tr("The font DejaVu Sans is missing (package fonts-dejavu-core)."))


class _NumberedCanvas(pdf_canvas.Canvas):
    """Holds pages back so the footer can say "page x of y"."""

    footer = ""
    middle = ""
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
            self.drawString(18 * mm + 6, 10 * mm, self.footer)  # where the text of the page starts
            self.drawCentredString(A4[0] / 2, 10 * mm, self.middle)
            page = tr("Page {page} of {total}", page=self._pageNumber, total=total)
            self.drawRightString(A4[0] - 18 * mm - 6, 10 * mm, page)
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


class SignatureBox(Flowable):
    """A signature written on the pad that stands for the line: its line lies on this one,
    what was written below it hangs below. Never taller above the line than the room there."""

    def __init__(self, data: bytes, width: float, baseline: float, ratio: float):
        super().__init__()
        self.data, self.baseline = data, baseline
        self.box_width = min(width, _SIGNATURE_HEIGHT / baseline * ratio)
        self.box_height = self.box_width / ratio

    def wrap(self, availWidth, availHeight):
        return self.box_width, self.box_height * self.baseline

    def draw(self):
        below = self.box_height * (1 - self.baseline)
        self.canv.drawImage(ImageReader(io.BytesIO(self.data)), 0, -below, self.box_width,
                            self.box_height, mask="auto")


def _signature_image(data: bytes, width: float) -> Flowable:
    """As large as the space above the line allows, without distorting it; one written on
    the pad keeps where it stood on its line."""
    with PilImage.open(io.BytesIO(data)) as source:
        ratio = source.width / source.height
        baseline = source.info.get("baseline")
    if baseline:
        return SignatureBox(data, width, float(baseline), ratio)
    height = min(_SIGNATURE_HEIGHT, width / ratio)
    return Image(io.BytesIO(data), width=height * ratio, height=height, hAlign="LEFT")


def _draw_marks(image: PilImage.Image, marks) -> None:
    """Numbered frames as on screen, sized to the picture so they read when printed small."""
    draw = ImageDraw.Draw(image)
    line = max(2, image.width // 300)
    radius = max(10, image.width // 50)
    font = ImageFont.load_default(size=int(radius * 1.3))
    for mark in marks:
        left, top = mark.x * image.width, mark.y * image.height
        right, bottom = left + mark.w * image.width, top + mark.h * image.height
        draw.rectangle((left, top, right, bottom), outline=_MARK_RGB, width=line)
        draw.ellipse((left - radius, top - radius, left + radius, top + radius), fill=_MARK_RGB)
        draw.text((left, top), str(mark.number), fill="white", font=font, anchor="mm")


def _photo(path: Path, width: float, marks=(), view=None) -> Image | None:
    """From the proxy: as it is without marks and view, so its bytes go into the file
    unchanged; otherwise turned and cut as the view says, then marked."""
    proxy = make_proxy(path)
    plain = view is None or view.plain
    if proxy is not None and not marks and plain:
        with PilImage.open(proxy) as header:
            ratio = header.height / header.width
        return Image(str(proxy), width=width, height=width * ratio)
    if proxy is not None:
        with PilImage.open(proxy) as source:
            image = source.convert("RGB")
    else:
        image = reduced(path)
        if image is None:
            return None
    if not plain:
        image = view.apply(image)
    _draw_marks(image, marks)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=QUALITY)
    buffer.seek(0)
    return Image(buffer, width=width, height=width * image.height / image.width)


def _photos(items: list[tuple], width: float) -> list[Image | None]:
    """All photos of a block at once: decoding and scaling run beside each other on every core,
    as the imaging library lets go of the interpreter while it works."""
    def one(item: tuple) -> Image | None:
        return _photo(item[0], width, item[2] if len(item) > 2 else (),
                      item[5] if len(item) > 5 else None)
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as pool:
        return list(pool.map(one, items))
