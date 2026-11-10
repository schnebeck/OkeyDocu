# EasyMeasurement - easymeasurement/ui/photo_timeline_model.py
# Time-to-pixel mapping, ruler ticks and drag decisions of the photo timeline.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from ..l10n import plural, tr

EPOCH = datetime(2000, 1, 1)  # a midnight, so whole hours fall on round numbers
MIN_GAP_S = 5
GUTTER_PX = 74  # the track names stand left of the time axis
FIT_LEFT_PX = 10
FIT_RIGHT_PX = 96  # a thumbnail reaches to the right of its moment
MIN_FIT_SPAN_S = 120.0
MAX_PX_PER_S = 40.0
ZOOM_OUT_LIMIT = 4.0  # how far the wheel goes beyond the fitted view
TICK_MIN_PX = 84
TICK_STEPS = (
    1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 10800, 21600, 43200,
    86400, 172800, 604800,
)
GAP_STEPS = (30, 60, 120, 300, 600, 900, 1800, 3600, 7200, 14400, 28800, 86400)
GAP_DEFAULT_PX = 80
LIFT_MARGIN_PX = 6
MIN_THUMB_PX = 28
MAX_THUMB_PX = 110


def to_seconds(moment: datetime) -> float:
    return (moment - EPOCH).total_seconds()


def to_moment(seconds: float) -> datetime:
    return EPOCH + timedelta(seconds=seconds)


class TimeAxis:
    """Maps seconds to pixels of the view. Everything on the tracks is placed through it."""

    def __init__(self, width: float = 800.0):
        self.width = width
        self.left = GUTTER_PX  # pixels left of this lie under the track names
        self.start = 0.0
        self.px_per_s = 1.0
        self.min_px_per_s = 1e-5

    def x_of(self, seconds: float) -> float:
        return (seconds - self.start) * self.px_per_s

    def seconds_at(self, x: float) -> float:
        return self.start + x / self.px_per_s

    def shows(self, low: float, high: float) -> bool:
        return self.x_of(low) >= self.left and self.x_of(high) <= self.width

    def fit(self, low: float, high: float, right: float = FIT_RIGHT_PX) -> None:
        room = max(self.width - self.left - FIT_LEFT_PX - right, 1.0)
        self.px_per_s = min(room / max(high - low, MIN_FIT_SPAN_S), MAX_PX_PER_S)
        self.min_px_per_s = self.px_per_s / ZOOM_OUT_LIMIT
        centre_px = self.left + FIT_LEFT_PX + room / 2
        self.start = (low + high) / 2 - centre_px / self.px_per_s

    def zoom_at(self, x: float, factor: float) -> None:
        """The moment under the pointer stays under the pointer."""
        anchor = self.seconds_at(x)
        self.px_per_s = min(max(self.px_per_s * factor, self.min_px_per_s), MAX_PX_PER_S)
        self.start = anchor - x / self.px_per_s

    def pan(self, dx: float) -> None:
        self.start -= dx / self.px_per_s

    def keep_near(self, low: float, high: float) -> None:
        """Panning stops before the content has left the view for good."""
        span = (self.width - self.left) / self.px_per_s
        lead = self.left / self.px_per_s
        self.start = min(max(self.start, low - lead - span * 0.8), high - lead - span * 0.2)


def tick_step(px_per_s: float) -> int:
    for step in TICK_STEPS:
        if step * px_per_s >= TICK_MIN_PX:
            return step
    return TICK_STEPS[-1]


def tick_text(seconds: float, step: int) -> str:
    moment = to_moment(seconds)
    if moment.hour == moment.minute == moment.second == 0:
        return tr("{month}-{day}", month=f"{moment.month:02d}", day=f"{moment.day:02d}")
    return moment.strftime("%H:%M:%S" if step < 60 else "%H:%M")


def ticks(axis: TimeAxis) -> list[tuple[float, str]]:
    """Ruler marks on round clock times: (x, label)."""
    step = tick_step(axis.px_per_s)
    seconds = math.ceil(axis.start / step) * step
    found = []
    while (x := axis.x_of(seconds)) <= axis.width:
        if x >= axis.left:
            found.append((x, tick_text(seconds, step)))
        seconds += step
    return found


def duration_text(seconds: float) -> str:
    """A span in plain words: 45 s, 2 min 30 s, 1 h 5 min, 2 days 3 h."""
    total = round(abs(seconds))
    days, rest = divmod(total, 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    if days:
        parts = [plural(days, "{count} day", "{count} days"), f"{hours} h" if hours else ""]
    elif hours:
        parts = [f"{hours} h", f"{minutes} min" if minutes else ""]
    elif minutes:
        parts = [f"{minutes} min", f"{secs} s" if secs else ""]
    else:
        parts = [f"{secs} s"]
    return " ".join(part for part in parts if part)


def shift_text(seconds: float) -> str:
    if round(seconds) == 0:
        return tr("Photos at their time taken")
    if seconds > 0:
        return tr("Photos {duration} later", duration=duration_text(seconds))
    return tr("Photos {duration} earlier", duration=duration_text(seconds))


def default_gap_seconds(px_per_s: float) -> int:
    """Long enough to be seen at this zoom, and a round number."""
    wanted = GAP_DEFAULT_PX / px_per_s
    return next((step for step in GAP_STEPS if step >= wanted), GAP_STEPS[-1])


def stretched_gap(seconds: float, dx: float, px_per_s: float) -> int:
    return max(MIN_GAP_S, round(seconds + dx / px_per_s))


@dataclass(frozen=True)
class Tracks:
    """The bands of the view from top to bottom. Thumbnails take what is left."""

    height: int
    ruler: int = 20
    label: int = 15
    mark: int = 16
    links: int = 20

    @property
    def mark_y(self) -> float:
        return self.ruler + self.label + self.mark / 2

    @property
    def marks_bottom(self) -> int:
        return self.ruler + self.label + self.mark + 3

    @property
    def photos_top(self) -> int:
        return self.marks_bottom + self.links

    @property
    def thumb_height(self) -> int:
        return min(max(self.height - self.photos_top - 4, MIN_THUMB_PX), MAX_THUMB_PX)


class Zone(Enum):
    """What letting go of a dragged thumbnail would do at this pointer position."""

    SHIFT = "shift"  # all timeline photos move together
    PIN = "pin"  # this photo goes to the measurement under the pointer
    HOLD = "hold"  # nothing: a pinned photo has no strip to slide along
    LIFT = "lift"  # it leaves the timeline for another widget


def drag_zone(
    x: float, y: float, width: float, tracks: Tracks, follows_time: bool, can_pin: bool
) -> Zone:
    """Sideways in its own track moves all, up into the measurements takes only this one.

    The strip of links still belongs to the photo track, so a hand that drifts a little
    during a long sideways drag does not change the meaning.
    """
    if not -LIFT_MARGIN_PX <= y <= tracks.height + LIFT_MARGIN_PX:
        return Zone.LIFT
    if y < tracks.marks_bottom:
        inside = -LIFT_MARGIN_PX <= x <= width + LIFT_MARGIN_PX
        return Zone.LIFT if not inside else Zone.PIN if can_pin else Zone.HOLD
    if follows_time:
        return Zone.SHIFT
    return Zone.HOLD if -LIFT_MARGIN_PX <= x <= width + LIFT_MARGIN_PX else Zone.LIFT
