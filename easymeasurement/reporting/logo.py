# EasyMeasurement - easymeasurement/reporting/logo.py
# Prepares logo images for embedding in a template.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import base64
import hashlib
import io

from PIL import Image, ImageOps, UnidentifiedImageError

from ..l10n import tr

PAGE_WIDTH_MM = 210.0
PAGE_HEIGHT_MM = 297.0
MARGIN_MM = 18.0
MIN_WIDTH_MM = 5.0

_MAX_PIXELS = 1000  # about 500 dpi at 50 mm, plenty for print
_MAX_BYTES = 1_500_000


class LogoError(Exception):
    """The file cannot be used as a logo."""


def prepare_logo(data: bytes) -> tuple[str, str]:
    """Normalise an image and return (key, base64 text) for the template.

    The key is derived from the content, so the same logo is stored only once.
    Transparency is kept.
    """
    try:
        with Image.open(io.BytesIO(data)) as source:
            image = ImageOps.exif_transpose(source)
            image.load()
    except (UnidentifiedImageError, OSError, ValueError) as err:
        raise LogoError(tr("The file is not a readable image.")) from err
    has_alpha = image.mode in ("RGBA", "LA") or "transparency" in image.info
    image = image.convert("RGBA" if has_alpha else "RGB")
    image.thumbnail((_MAX_PIXELS, _MAX_PIXELS))
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    if buffer.tell() > _MAX_BYTES and not has_alpha:
        buffer = io.BytesIO()  # photo-like logos compress far better as JPEG
        image.save(buffer, "JPEG", quality=88)
    if buffer.tell() > _MAX_BYTES:
        raise LogoError(tr("The image is too large. Please choose a smaller file."))
    encoded = buffer.getvalue()
    return hashlib.sha256(encoded).hexdigest()[:12], base64.b64encode(encoded).decode("ascii")


def decode_logo(text: str) -> bytes:
    try:
        return base64.b64decode(text, validate=True)
    except ValueError as err:
        raise LogoError(tr("The image data in the template is damaged.")) from err


def logo_ratio(data: bytes) -> float:
    """Height divided by width."""
    with Image.open(io.BytesIO(data)) as image:
        return image.height / image.width


def clamp_placement(x: float, y: float, width: float, ratio: float) -> tuple[float, float, float]:
    """Keep a logo on the page, without changing its proportions."""
    width = max(MIN_WIDTH_MM, min(width, PAGE_WIDTH_MM, PAGE_HEIGHT_MM / ratio))
    x = max(0.0, min(x, PAGE_WIDTH_MM - width))
    y = max(0.0, min(y, PAGE_HEIGHT_MM - width * ratio))
    return x, y, width


# Quick positions: label and a function of (width, height) returning (x, y).
PRESETS = [
    ("Oben links", lambda w, h: (MARGIN_MM, 8.0)),
    ("Oben Mitte", lambda w, h: ((PAGE_WIDTH_MM - w) / 2, 8.0)),
    ("Oben rechts", lambda w, h: (PAGE_WIDTH_MM - MARGIN_MM - w, 8.0)),
    ("Unten links", lambda w, h: (MARGIN_MM, PAGE_HEIGHT_MM - 16.0 - h)),
    ("Unten Mitte", lambda w, h: ((PAGE_WIDTH_MM - w) / 2, PAGE_HEIGHT_MM - 16.0 - h)),
    ("Unten rechts", lambda w, h: (PAGE_WIDTH_MM - MARGIN_MM - w, PAGE_HEIGHT_MM - 16.0 - h)),
]


def trimmed(data: bytes) -> bytes:
    """The logo without the empty border around it, transparent or white, so it can stand
    flush with the edge of the printed area."""
    with Image.open(io.BytesIO(data)) as source:
        image = source.convert("RGBA")
    alpha = image.getchannel("A")
    box = alpha.getbbox()
    if box is not None and alpha.getextrema()[0] == 255:  # opaque: the border is white
        inked = ImageOps.invert(image.convert("L")).point(lambda level: 255 if level > 8 else 0)
        box = inked.getbbox() or box
    if box is None or box == (0, 0, image.width, image.height):
        return data
    buffer = io.BytesIO()
    image.crop(box).save(buffer, "PNG")
    return buffer.getvalue()
