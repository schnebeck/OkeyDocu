# EasyMeasurement - easymeasurement/campaign/photo_view.py
# How a photo is shown: turned by quarter turns and cut to a part, the original untouched.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The original file stays the evidence. A view turns it clockwise by `rotation` degrees and
then keeps the part `crop` of the turned picture, given as fractions (x, y, width, height).
Marks are kept in fractions of what the view shows; `move_mark` carries a mark from one view
to another, so it stays on the same spot of the photo."""
from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

TURNS = (0, 90, 180, 270)
WHOLE = (0.0, 0.0, 1.0, 1.0)
_SMALLEST = 0.005  # a mark cut down to less than this, as a part of the view, is gone


@dataclass(frozen=True)
class PhotoView:
    rotation: int = 0
    crop: tuple[float, float, float, float] = WHOLE

    @classmethod
    def stored(cls, rotation: int | None, crop: str | None) -> "PhotoView":
        parts = tuple(float(part) for part in (crop or "").split())
        return cls(rotation or 0, parts if len(parts) == 4 else WHOLE)

    def crop_text(self) -> str:
        return "" if self.crop == WHOLE else " ".join(f"{part:.6f}" for part in self.crop)

    @property
    def plain(self) -> bool:
        return self.rotation == 0 and self.crop == WHOLE

    def turned(self, quarter: int) -> "PhotoView":
        """Turned on by quarter turns, clockwise for a positive number; the part kept turns
        along, so it shows the same piece of the photo."""
        rotation = (self.rotation + 90 * quarter) % 360
        x, y, w, h = self.crop
        for _ in range(quarter % 4):
            x, y, w, h = 1 - y - h, x, h, w
        return PhotoView(rotation, (x, y, w, h))

    def cut(self, part: tuple[float, float, float, float]) -> "PhotoView":
        """Keeps `part` of what the view shows now."""
        x, y, w, h = self.crop
        px, py, pw, ph = part
        return PhotoView(self.rotation, (x + px * w, y + py * h, pw * w, ph * h))

    def whole(self) -> "PhotoView":
        return PhotoView(self.rotation)

    # Points: from the original into the view and back, all as fractions ----------------

    def _to_turned(self, u: float, v: float) -> tuple[float, float]:
        return {0: (u, v), 90: (1 - v, u), 180: (1 - u, 1 - v), 270: (v, 1 - u)}[self.rotation]

    def _from_turned(self, x: float, y: float) -> tuple[float, float]:
        return {0: (x, y), 90: (y, 1 - x), 180: (1 - x, 1 - y), 270: (1 - y, x)}[self.rotation]

    def into(self, u: float, v: float) -> tuple[float, float]:
        x, y = self._to_turned(u, v)
        cx, cy, cw, ch = self.crop
        return (x - cx) / cw, (y - cy) / ch

    def out_of(self, a: float, b: float) -> tuple[float, float]:
        cx, cy, cw, ch = self.crop
        return self._from_turned(cx + a * cw, cy + b * ch)

    # Pictures ------------------------------------------------------------------------

    def apply(self, image: Image.Image) -> Image.Image:
        if self.rotation:
            turn = {90: Image.Transpose.ROTATE_270, 180: Image.Transpose.ROTATE_180,
                    270: Image.Transpose.ROTATE_90}[self.rotation]
            image = image.transpose(turn)
        if self.crop != WHOLE:
            x, y, w, h = self.crop
            box = (round(x * image.width), round(y * image.height),
                   round((x + w) * image.width), round((y + h) * image.height))
            image = image.crop(box)
        return image


def move_mark(mark, old: PhotoView, new: PhotoView):
    """The mark carried from what `old` shows to what `new` shows; None once it is cut away."""
    corners = [old.out_of(mark.x, mark.y), old.out_of(mark.x + mark.w, mark.y + mark.h)]
    points = [new.into(u, v) for u, v in corners]
    left = max(min(p[0] for p in points), 0.0)
    top = max(min(p[1] for p in points), 0.0)
    right = min(max(p[0] for p in points), 1.0)
    bottom = min(max(p[1] for p in points), 1.0)
    if right - left < _SMALLEST or bottom - top < _SMALLEST:
        return None
    return type(mark)(mark.number, left, top, right - left, bottom - top, mark.text)
