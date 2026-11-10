# EasyMeasurement - easymeasurement/ui/photo_timeline_gestures.py
# What one held mouse button does: pan, move a photo, or stretch a gap.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication

from ..l10n import plural, tr
from .photo_timeline_data import TrackGap, TrackPhoto
from .photo_timeline_model import (
    Zone,
    drag_zone,
    duration_text,
    shift_text,
    stretched_gap,
    to_moment,
)

HANG_PX = 10  # a floating thumbnail hangs this far under the pointer


class Gesture:
    """Follows the pointer from press to release. Below the drag distance it is a click."""

    def __init__(self, view, pos: QPoint):
        self.view = view
        self.origin = pos
        self.active = False

    def passed_distance(self, pos: QPoint) -> bool:
        if not self.active:
            distance = (pos - self.origin).manhattanLength()
            self.active = distance >= QApplication.startDragDistance()
        return self.active

    def move(self, pos: QPoint) -> None:
        raise NotImplementedError

    def release(self) -> None:
        raise NotImplementedError

    def cancel(self) -> None:
        """Leave everything as it was before the press."""


class PanGesture(Gesture):
    def __init__(self, view, pos: QPoint, on_click: Callable[[], None]):
        super().__init__(view, pos)
        self.last = pos
        self.on_click = on_click

    def move(self, pos: QPoint) -> None:
        if not self.passed_distance(pos):
            return
        self.view.pan_by(pos.x() - self.last.x())
        self.last = pos

    def release(self) -> None:
        if not self.active:
            self.on_click()


class PhotoGesture(Gesture):
    """The zone under the pointer decides at every step, so the meaning can change
    during the drag and what the tracks show is always what letting go would do."""

    def __init__(self, view, pos: QPoint, photo: TrackPhoto):
        super().__init__(view, pos)
        self.photo = photo
        self.start_shift = view.data.shift
        self.grabbed_at = view.axis.seconds_at(pos.x())
        self.zone: Zone | None = None
        self.target = None
        self.lifted = False

    def move(self, pos: QPoint) -> None:
        if not self.passed_distance(pos):
            return
        view = self.view
        data, axis = view.data, view.axis
        self.zone = drag_zone(
            pos.x(), pos.y(), axis.width, view.tracks, self.photo.follows_time, bool(data.marks)
        )
        if self.zone is Zone.LIFT:
            self.lifted = True
            self.cancel()
            return
        data.shift = self.start_shift
        if self.zone is Zone.SHIFT:
            data.shift += round(axis.seconds_at(pos.x()) - self.grabbed_at)
        self.target = data.nearest_mark(axis.seconds_at(pos.x())) if self.zone is Zone.PIN else None
        view.set_target(self.target.id if self.target else None)
        if self.zone is Zone.SHIFT:
            view.set_float(None)
        elif self.zone is Zone.PIN:
            view.set_float(self.photo.id, pos.x(), pos.y() + HANG_PX)
        else:
            view.set_float(self.photo.id, pos.x(), view.tracks.photos_top)
        view.place_photos()
        view.shift_moved.emit(data.shift)
        view.hint.emit(self._words())

    def _words(self) -> str:
        if self.zone is Zone.SHIFT:
            changes = self.view.data.changed_owners()
            words = tr("Move all photos: {shift}", shift=shift_text(self.view.data.shift))
            if not changes:
                return words
            return words + " · " + plural(changes, "{count} photo changes its measurement",
                                          "{count} photos change their measurement")
        if self.zone is Zone.PIN and self.target:
            moment = to_moment(self.target.at).strftime("%H:%M:%S")
            return tr("Let go: pin only this photo to {mark} {moment}", mark=self.target.label,
                      moment=moment)
        return tr("This photo stays at its measurement. To change, drag it up onto a"
                  " measurement.")

    def release(self) -> None:
        view = self.view
        if not self.active:
            return
        zone, target, shift = self.zone, self.target, view.data.shift
        self.cancel()
        if zone is Zone.SHIFT and shift != self.start_shift:
            view.shift_done.emit(shift)
        elif zone is Zone.PIN and target:
            if self.photo.follows_time or target.id != self.photo.owner:
                view.pin_done.emit(self.photo.id, target.id)

    def cancel(self) -> None:
        view = self.view
        view.data.shift = self.start_shift
        self.target = None
        view.set_target(None)
        view.set_float(None)
        view.place_photos()
        view.shift_moved.emit(self.start_shift)


class GapGesture(Gesture):
    def __init__(self, view, pos: QPoint, gap: TrackGap):
        super().__init__(view, pos)
        self.gap = gap
        self.start_seconds = gap.seconds

    def move(self, pos: QPoint) -> None:
        if not self.passed_distance(pos):
            return
        view = self.view
        self.gap.seconds = stretched_gap(
            self.start_seconds, pos.x() - self.origin.x(), view.axis.px_per_s
        )
        view.place_photos()
        view.hint.emit(tr("Gap {duration}: the photos after it move along",
                          duration=duration_text(self.gap.seconds)))

    def release(self) -> None:
        seconds = self.gap.seconds
        if seconds != self.start_seconds:
            self.gap.seconds = self.start_seconds
            self.view.gap_resized.emit(self.gap.id, seconds)

    def cancel(self) -> None:
        self.gap.seconds = self.start_seconds
        self.view.place_photos()
