# EasyMeasurement - easymeasurement/ui/photo_timeline_mouse.py
# Turns the pointer into gestures, and says in the hint line what they would do.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtGui import QCursor

from .photo_shared import start_photo_drag
from .photo_timeline_gestures import GapGesture, Gesture, PanGesture, PhotoGesture
from .photo_timeline_model import Zone, to_moment

EDGE_PX = 28  # near the view's edge a shift keeps going by itself
EDGE_STEP_PX = 14
EDGE_TICK_MS = 40

IDLE_HINT = (
    "Foto seitlich ziehen: alle Fotos verschieben · Foto auf eine Messung ziehen: nur dieses"
)
READ_ONLY_HINT = "Abgeschlossene Kampagne: nur ansehen. Doppelklick zeigt ein Foto groß."
HOVER_HINTS = {
    "pinned": "Angeheftet: bleibt bei seiner Messung · Auf eine andere Messung ziehen · "
              "Rechtsklick: wieder der Zeit folgen",
    "photo": "Seitlich ziehen: alle Fotos verschieben · Nach oben auf eine Messung ziehen: "
             "nur dieses Foto · Doppelklick: groß",
    "mark": "Klick: diese Messung in der Tabelle zeigen",
    "gap": "Lücke: die Fotos danach stehen später · Rechte Kante ziehen zum Dehnen",
    "gap_grip": "Ziehen: Lücke dehnen oder kürzen",
    "gap_close": "Klick: Lücke entfernen, die Fotos rücken zurück",
    "strip": "Ziehen: Ansicht bewegen · Mausrad: zoomen · Rechtsklick: Lücke hier einfügen",
}
CURSORS = {
    "pinned": Qt.CursorShape.OpenHandCursor, "photo": Qt.CursorShape.OpenHandCursor,
    "mark": Qt.CursorShape.PointingHandCursor, "gap_close": Qt.CursorShape.PointingHandCursor,
    "gap_grip": Qt.CursorShape.SizeHorCursor,
}


class TrackMouse:
    """Holds the gesture in progress. There is never more than one."""

    def __init__(self, view):
        self.view = view
        self.gesture: Gesture | None = None
        self.last = QPoint()
        self.edge_timer = QTimer(view, interval=EDGE_TICK_MS)
        self.edge_timer.timeout.connect(self._edge_tick)

    def idle_hint(self) -> str:
        return READ_ONLY_HINT if self.view.read_only else IDLE_HINT

    def press(self, pos: QPoint) -> None:
        view = self.view
        hit = view.hit(pos)
        self.last = pos
        view.thumbs.pause(True)
        if hit.kind == "photo":
            view.set_selected(hit.id)
            if view.read_only:
                self.gesture = PanGesture(view, pos, lambda: None)
            else:
                self.gesture = PhotoGesture(view, pos, view.data.photo(hit.id))
                view.viewport().setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
        elif hit.kind == "gap_grip":
            self.gesture = GapGesture(view, pos, view.data.gap(hit.id))
        elif hit.kind == "gap_close":
            self.gesture = PanGesture(view, pos, lambda: view.gap_closed.emit(hit.id))
        elif hit.kind == "mark":
            self.gesture = PanGesture(view, pos, lambda: self._choose(hit.id))
        else:
            self.gesture = PanGesture(view, pos, lambda: self._clear())

    def _choose(self, mark_id: int) -> None:
        self.view.choose_mark(mark_id)
        self.view.mark_clicked.emit(mark_id)

    def _clear(self) -> None:
        self.view.choose_mark(None)
        self.view.set_selected(None)

    def move(self, pos: QPoint) -> None:
        self.last = pos
        if self.gesture is None:
            self._hover(pos)
            return
        self.gesture.move(pos)
        if isinstance(self.gesture, PhotoGesture):
            if self.gesture.lifted:
                self._lift(self.gesture.photo.id)
            elif self.gesture.zone is Zone.SHIFT and self._edge_direction():
                self.edge_timer.start()

    def _lift(self, photo_id: int) -> None:
        """The pointer left the view with a photo: hand it to whatever takes a drop."""
        view = self.view
        self.gesture = None
        self.edge_timer.stop()
        view.thumbs.pause(False)
        view.hint.emit("Loslassen auf dem Stapel, einer Messung oder der Messwerttabelle")
        item = view.photo_items[photo_id]
        start_photo_drag(view.viewport(), photo_id, item.pixmap)
        view.hint.emit(self.idle_hint())

    def _edge_direction(self) -> int:
        if self.last.x() < self.view.axis.left + EDGE_PX:
            return 1
        return -1 if self.last.x() > self.view.axis.width - EDGE_PX else 0

    def _edge_tick(self) -> None:
        direction = self._edge_direction()
        gesture = self.gesture
        if not direction or not isinstance(gesture, PhotoGesture) or gesture.zone is not Zone.SHIFT:
            self.edge_timer.stop()
            return
        self.view.axis.pan(direction * EDGE_STEP_PX)
        self.view.fitted = False
        self.view.relayout()
        gesture.move(self.last)

    def release(self) -> None:
        gesture, self.gesture = self.gesture, None
        self.edge_timer.stop()
        self.view.thumbs.pause(False)
        if gesture is not None:
            gesture.release()
            self._hover(self.last)

    def cancel(self) -> None:
        gesture, self.gesture = self.gesture, None
        self.edge_timer.stop()
        self.view.thumbs.pause(False)
        if gesture is not None:
            gesture.cancel()
            self.view.hint.emit(self.idle_hint())

    def _hover(self, pos: QPoint) -> None:
        view = self.view
        hit = view.hit(pos)
        kind = hit.kind
        if kind == "photo":
            view.set_hovered(hit.id)
            if not view.data.photo(hit.id).follows_time:
                kind = "pinned"
        else:
            view.set_hovered(None)
        editing = not view.read_only or kind == "mark"
        words = HOVER_HINTS.get(kind) if editing else None
        view.hint.emit(words or self.idle_hint())
        cursor = CURSORS.get(kind) if editing else None
        if cursor is None:
            view.viewport().unsetCursor()
        else:
            view.viewport().setCursor(QCursor(cursor))

    # A photo carried in from another widget -------------------------------

    def carried_over(self, pos: QPoint) -> None:
        view = self.view
        if pos.y() < view.tracks.marks_bottom:
            mark = view.data.nearest_mark(view.axis.seconds_at(pos.x()))
            view.set_target(mark.id if mark else None)
            if mark:
                moment = to_moment(mark.at).strftime("%H:%M:%S")
                view.hint.emit(f"Loslassen: Foto an {mark.label} {moment} heften")
        else:
            view.set_target(None)
            view.hint.emit("Loslassen: Foto folgt wieder seiner Aufnahmezeit")

    def carried_away(self) -> None:
        self.view.set_target(None)
        self.view.hint.emit(self.idle_hint())

    def carried_in(self, photo_id: int, pos: QPoint) -> None:
        view = self.view
        target = view.target_mark
        self.carried_away()
        if pos.y() >= view.tracks.marks_bottom:
            view.photo_returned.emit(photo_id)
        elif target is not None:
            view.pin_done.emit(photo_id, target)
