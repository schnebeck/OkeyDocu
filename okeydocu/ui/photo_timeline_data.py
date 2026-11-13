# OkeyDocu - okeydocu/ui/photo_timeline_data.py
# A snapshot of what the timeline shows, kept in plain values for fast live dragging.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from ..campaign.photos import timeline_time
from ..l10n import tr
from .photo_timeline_model import to_moment, to_seconds

TIMELINE, PINNED = "timeline", "pinned"


@dataclass(frozen=True)
class TrackMark:
    id: int
    at: float
    verdict: str
    label: str


@dataclass
class TrackPhoto:
    id: int
    placement: str
    owner: int | None
    taken: datetime | None
    name: str
    file_name: str

    @property
    def follows_time(self) -> bool:
        return self.placement == TIMELINE


@dataclass
class TrackGap:
    id: int
    at: datetime
    seconds: float


class TimelineData:
    """Measurements, placed photos and gaps. `shift` and a gap's `seconds` may run ahead
    of the database while something is dragged."""

    def __init__(self, marks: list[TrackMark], photos: list[TrackPhoto],
                 gaps: list[TrackGap], shift: float = 0.0):
        self.marks = sorted(marks, key=lambda mark: mark.at)
        self.photos = photos
        self.gaps = gaps
        self.shift = shift
        self.marks_by_id = {mark.id: mark for mark in self.marks}
        first_at_time = {}
        for mark in self.marks:
            first_at_time.setdefault(mark.at, mark)
        self._distinct = list(first_at_time.values())
        self._times = list(first_at_time)

    @classmethod
    def from_rows(cls, measurements, photos, gaps, shift: float,
                  label: Callable[[str], str]) -> TimelineData:
        marks = [
            TrackMark(row["id"], to_seconds(datetime.fromisoformat(row["local_time"])),
                      row["verdict"], label(row["function"]))
            for row in measurements
        ]
        placed = [
            TrackPhoto(
                row["id"], row["placement"], row["measurement_id"],
                datetime.fromisoformat(row["taken_at"]) if row["taken_at"] else None,
                row["original_name"], row["file_name"],
            )
            for row in photos if row["placement"] in (TIMELINE, PINNED)
        ]
        stops = [
            TrackGap(row["id"], datetime.fromisoformat(row["at"]), row["seconds"])
            for row in gaps
        ]
        return cls(marks, placed, stops, shift)

    def photo(self, photo_id: int) -> TrackPhoto | None:
        return next((photo for photo in self.photos if photo.id == photo_id), None)

    def gap(self, gap_id: int) -> TrackGap | None:
        return next((gap for gap in self.gaps if gap.id == gap_id), None)

    def _pairs(self) -> list[tuple[datetime, float]]:
        return [(gap.at, gap.seconds) for gap in self.gaps]

    def nearest_mark(self, seconds: float) -> TrackMark | None:
        """Like the assignment in the backend: the closest, at equal distance the earlier."""
        if not self._times:
            return None
        index = bisect_left(self._times, seconds)
        if index == 0:
            return self._distinct[0]
        if index == len(self._times):
            return self._distinct[-1]
        before, after = self._times[index - 1], self._times[index]
        return self._distinct[index - 1 if seconds - before <= after - seconds else index]

    def places(self) -> dict[int, float]:
        """Where each photo stands. A pinned one stands at its measurement."""
        pairs = self._pairs()
        found = {}
        for photo in self.photos:
            if photo.follows_time:
                found[photo.id] = to_seconds(timeline_time(photo.taken, self.shift, pairs))
            elif photo.owner in self.marks_by_id:
                found[photo.id] = self.marks_by_id[photo.owner].at
        return found

    def owners(self, places: dict[int, float]) -> dict[int, int | None]:
        """The measurement of each placed photo at the present shift."""
        found = {}
        for photo in self.photos:
            if photo.id in places:
                if photo.follows_time:
                    mark = self.nearest_mark(places[photo.id])
                    found[photo.id] = mark.id if mark else None
                else:
                    found[photo.id] = photo.owner
        return found

    def changed_owners(self) -> int:
        """How many photos would change their measurement if this were stored."""
        owners = self.owners(self.places())
        return sum(1 for photo in self.photos if photo.id in owners
                   and owners[photo.id] != photo.owner)

    def gap_spans(self) -> dict[int, tuple[float, float]]:
        """Each gap as a block on the time axis. Gaps at the same moment stand in a row."""
        spans = {}
        before: list[tuple[datetime, float]] = []
        for gap in self.gaps:
            start = to_seconds(timeline_time(gap.at, self.shift, before))
            spans[gap.id] = (start, start + gap.seconds)
            before.append((gap.at, gap.seconds))
        return spans

    def original_time(self, seconds: float) -> datetime:
        """The time of taking that stands at this place: `timeline_time` turned around.

        Inside a gap that is the moment the gap starts from.
        """
        pushed = 0.0
        for gap in self.gaps:
            start = to_seconds(gap.at) + self.shift + pushed
            if seconds < start:
                break
            if seconds < start + gap.seconds:
                return gap.at
            pushed += gap.seconds
        return to_moment(seconds - self.shift - pushed)

    def first_taken(self) -> datetime | None:
        return min((p.taken for p in self.photos if p.follows_time), default=None)

    def first_place(self) -> datetime | None:
        first = self.first_taken()
        return timeline_time(first, self.shift, self._pairs()) if first else None

    def shift_for_start(self, start: datetime) -> float | None:
        """The shift that puts the first photo at `start`, gaps before it included."""
        first = self.first_taken()
        if first is None:
            return None
        return (start - timeline_time(first, 0.0, self._pairs())).total_seconds()

    def content_range(self) -> tuple[float, float] | None:
        points = [mark.at for mark in self.marks] + list(self.places().values())
        for span in self.gap_spans().values():
            points.extend(span)
        return (min(points), max(points)) if points else None

    def empty_texts(self) -> tuple[str, str]:
        """What to say in a track with nothing in it, so that no box stays blank."""
        marks = "" if self.marks else tr("No measurements yet. They appear here by themselves.")
        photos = "" if self.photos else (
            tr("No photos here yet: import photos or drag them here from the stack.")
        )
        return marks, photos
