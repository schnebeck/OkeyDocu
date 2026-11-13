# OkeyDocu - okeydocu/campaign/photos.py
# Reads photo timestamps and matches photos to measurements.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

_EXIF_IFD = 0x8769
_DATETIME_ORIGINAL = 36867
_OFFSET_ORIGINAL = 36881
_NAME_RE = re.compile(r"(20\d{2})[-_]?(\d{2})[-_]?(\d{2})[-_ T]?(\d{2})[-_.]?(\d{2})[-_.]?(\d{2})")

DEFAULT_TOLERANCE = timedelta(minutes=2)
# If the second-best measurement is this close to the best, a person decides.
AMBIGUITY_MARGIN = timedelta(seconds=5)


def _to_local(moment: datetime) -> datetime:
    return moment.astimezone().replace(tzinfo=None) if moment.tzinfo else moment


def read_photo_time(path: Path) -> tuple[datetime | None, str]:
    """Return (naive local time, source). The file date is ignored on purpose:
    copying a photo from the phone resets it."""
    try:
        with Image.open(path) as image:
            exif = image.getexif().get_ifd(_EXIF_IFD)
    except OSError:
        exif = {}
    stamp = exif.get(_DATETIME_ORIGINAL)
    if stamp:
        offset = exif.get(_OFFSET_ORIGINAL)
        try:
            if offset:
                moment = datetime.strptime(f"{stamp}{offset}", "%Y:%m:%d %H:%M:%S%z")
            else:
                moment = datetime.strptime(stamp, "%Y:%m:%d %H:%M:%S")
            return _to_local(moment), "exif"
        except ValueError:
            pass
    match = _NAME_RE.search(path.name)
    if match:
        try:
            moment = datetime(*(int(g) for g in match.groups()))
        except ValueError:
            return None, "unknown"
        # Pixel phones name files in UTC, while the EXIF time is local.
        if path.name.startswith("PXL_"):
            moment = moment.replace(tzinfo=timezone.utc)
        return _to_local(moment), "filename"
    return None, "unknown"


def timeline_time(
    taken_at: datetime, shift_s: float, gaps: list[tuple[datetime, float]]
) -> datetime:
    """Where a photo stands on the timeline: moved by the shift and all gaps before it."""
    pushed = sum(seconds for at, seconds in gaps if at <= taken_at)
    return taken_at + timedelta(seconds=shift_s + pushed)


def nearest_measurement(
    moment: datetime, measurements: list[tuple[int, datetime]]
) -> int | None:
    """The closest measurement in time. At equal distance the earlier one."""
    if not measurements:
        return None
    return min(measurements, key=lambda m: (abs(m[1] - moment), m[1]))[0]
