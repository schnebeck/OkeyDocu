# EasyMeasurement - easymeasurement/campaign/photo_proxies.py
# Reduced copies of the photos for reports and thumbnails, kept in step with their originals.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A proxy lies in the campaign's `proxies` folder next to `photos` and `attachments`. Files
elsewhere get none and are reduced afresh each time. A proxy is named after its original
and its size. It carries the original's modification time: equal times mean the proxy was
made from the file as it is now, any other time means it is made again. Proxies are never
part of the seal; the originals stay the evidence, the proxies can always be thrown away."""

from __future__ import annotations

import os
import threading
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageOps

EDGE_PX = 1400  # the long side; at two photos side by side about 300 dpi on A4
QUALITY = 85  # goes into the report unchanged; one with marks is encoded a second time
FOLDER = "proxies"
HOMES = ("photos", "attachments")  # the folders of a campaign whose pictures get proxies
PART = ".part"

_warming = ThreadPoolExecutor(max_workers=max((os.cpu_count() or 2) - 1, 1),
                              thread_name_prefix="proxies")


def proxy_path(original: Path) -> Path | None:
    if original.parent.name not in HOMES:
        return None
    return original.parent.parent / FOLDER / f"{original.stem}-{EDGE_PX}.jpg"


def fresh_proxy(original: Path) -> Path | None:
    """The proxy if it was made from the original as it is now, else None."""
    proxy = proxy_path(original)
    try:
        if proxy is not None and proxy.stat().st_mtime_ns == original.stat().st_mtime_ns:
            return proxy
    except OSError:
        pass
    return None


def reduced(original: Path) -> Image.Image | None:
    """The picture upright and at most EDGE_PX along its long side; None if unreadable."""
    try:
        with Image.open(original) as source:
            # A JPEG decodes straight to a half, quarter or eighth: no full picture in memory.
            source.draft("RGB", (EDGE_PX, EDGE_PX))
            source.thumbnail((EDGE_PX, EDGE_PX))
            return ImageOps.exif_transpose(source).convert("RGB")
    except OSError:
        return None


def make_proxy(original: Path) -> Path | None:
    """The proxy, made first where it is missing or stale; None for an unreadable original
    and for a file outside a campaign's folders.

    Safe from several threads at once: each writes its own temporary file and moves it into
    place in one step, so a reader never sees half a picture.
    """
    proxy = fresh_proxy(original)
    if proxy is not None or proxy_path(original) is None:
        return proxy
    try:
        stat = original.stat()
    except OSError:
        return None
    image = reduced(original)
    if image is None:
        return None
    proxy = proxy_path(original)
    proxy.parent.mkdir(exist_ok=True)
    part = proxy.with_name(f"{proxy.name}.{os.getpid()}-{threading.get_ident()}{PART}")
    image.save(part, "JPEG", quality=QUALITY)
    os.utime(part, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    os.replace(part, proxy)
    return proxy


def warm_proxies(originals: Iterable[Path]) -> list[Future]:
    """Make missing proxies in the background, so the next report finds them ready.
    Returns one future for each proxy under way."""
    return [_warming.submit(make_proxy, original) for original in originals
            if proxy_path(original) is not None and fresh_proxy(original) is None]


def drop_proxy(original: Path) -> None:
    proxy = proxy_path(original)
    if proxy is not None:
        proxy.unlink(missing_ok=True)


def prune_proxies(folder: Path, originals: Iterable[Path]) -> int:
    """Remove proxies without an original, of another size, and leftovers of an interrupted
    write. Returns how many files went."""
    keep = {proxy.name for proxy in map(proxy_path, originals) if proxy is not None}
    gone = 0
    for entry in (folder / FOLDER).glob("*") if (folder / FOLDER).is_dir() else ():
        if entry.name not in keep and (not entry.name.endswith(PART) or _stale(entry)):
            entry.unlink(missing_ok=True)
            gone += 1
    return gone


def _stale(part: Path) -> bool:
    """A temporary file of this process may still be written by a worker."""
    return f".{os.getpid()}-" not in part.name


class ProxyMixin:
    """The campaign side: which originals a campaign has, tidying and warming their proxies."""

    def picture_files(self, campaign_id: int) -> list[Path]:
        photos = self.photos(campaign_id)
        return [self.photo_path(campaign_id, row["file_name"]) for row in photos] + [
            self.attachment_path(campaign_id, row["file_name"])
            for row in self.attachments(campaign_id) if row["file_name"]
        ]

    def tidy_proxies(self, campaign_id: int) -> int:
        return prune_proxies(self.folder(campaign_id), self.picture_files(campaign_id))

    def warm_proxies(self, campaign_id: int) -> list[Future]:
        return warm_proxies(self.picture_files(campaign_id))
