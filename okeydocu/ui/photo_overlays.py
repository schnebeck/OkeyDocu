# OkeyDocu - okeydocu/ui/photo_overlays.py
# What the timeline opens over itself: the start time, menu and tooltips.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import QDateTime
from PySide6.QtWidgets import QDateTimeEdit, QHBoxLayout, QLabel, QMenu, QPushButton, QWidget

from ..l10n import moment, qt_moment, tr
from ..model import Verdict
from ..reporting.context import VERDICT_TEXT
from .common import function_text, value_line
from .overlay import Overlay
from .photo_preview import PhotoPreview
from .photo_timeline_events import Hit
from .photo_timeline_model import duration_text, to_moment

class PhotoStartOverlay(Overlay):
    """Asks when the first photo stands on the timeline. All others keep their distance."""

    def __init__(self, place: datetime, taken: datetime, parent: QWidget):
        super().__init__(tr("Set the start of the photos"), parent, width=440)
        self.taken = taken
        self.ok_button.setText(tr("Apply"))
        self.body.addWidget(QLabel(
            tr("Where should the first photo stand? All other photos move along.")
        ))
        self.edit = QDateTimeEdit(QDateTime(place))
        self.edit.setDisplayFormat(qt_moment())
        self.edit.setCalendarPopup(True)
        reset = QPushButton(tr("Time taken"))
        reset.setToolTip(tr("The camera's time: {moment}", moment=moment(taken, seconds=True)))
        reset.clicked.connect(lambda: self.edit.setDateTime(QDateTime(taken)))
        row = QHBoxLayout()
        row.addWidget(self.edit, 1)
        row.addWidget(reset)
        self.body.addLayout(row)

    def first_field(self) -> QWidget:
        return self.edit

    @property
    def start(self) -> datetime:
        return self.edit.dateTime().toPython().replace(microsecond=0)


class TimelineAsking:
    """The part of the photo timeline that talks with the person over the tracks."""

    def _ask_start(self) -> None:
        data = self.view.data
        first = data.first_taken()
        if first is None:
            self.hint_label.setText(tr("There is no photo on the timeline yet."))
            return
        overlay = PhotoStartOverlay(data.first_place(), first, self)
        if overlay.exec():
            shift = data.shift_for_start(overlay.start)
            if shift != data.shift:
                self._shift(shift)

    def open_photo(self, photo_id: int) -> None:
        photo = self.view.data.photo(photo_id)
        if photo is not None:
            path = self.app.service.photo_path(self.campaign_id, photo.file_name)
            PhotoPreview(photo.name, self._photo_words(photo), path, self, self.app,
                         photo_id).exec()

    def _photo_words(self, photo) -> str:
        taken = moment(photo.taken, seconds=True) if photo.taken else tr("without time taken")
        mark = self.view.data.marks_by_id.get(photo.owner)
        where = f"{mark.label} {to_moment(mark.at):%H:%M:%S}" if mark else tr("no measurement")
        how = tr("pinned") if not photo.follows_time else tr("follows the time")
        return tr("Taken {taken} · {where} · {how}", taken=taken, where=where, how=how)

    def _describe(self, hit: Hit) -> str:
        if hit.kind == "photo":
            photo = self.view.data.photo(hit.id)
            return tr("{name}\n{words}\nDouble-click: show large", name=photo.name,
                      words=self._photo_words(photo))
        if hit.kind == "mark":
            row = self.rows[hit.id]
            lines = [function_text(row["function"]), row["local_time"].replace("T", "  "),
                     value_line(self.app.service, row), tr(VERDICT_TEXT[Verdict(row["verdict"])])]
            return "\n".join(line for line in lines if line)
        gap = self.view.data.gap(hit.id) if hit.kind.startswith("gap") else None
        return tr("Gap {duration}", duration=duration_text(gap.seconds)) if gap else ""

    def menu_entries(self, hit: Hit, seconds: float) -> list[tuple[str, Callable[[], None]]]:
        service = self.app.service
        entries = []
        if hit.kind == "photo":
            photo = self.view.data.photo(hit.id)
            entries.append((tr("Show large"), lambda: self.open_photo(hit.id)))
            if not self.read_only:
                entries.append((tr("Detach from the reading"),
                                lambda: self._write(service.stack_photo, hit.id)))
                if not photo.follows_time and photo.taken:
                    entries.append((tr("Follow the time again"),
                                    lambda: self._write(service.return_to_timeline, hit.id)))
                if photo.follows_time:
                    entries.append((tr("Insert gap before"), lambda: self._add_gap(photo.taken)))
        elif hit.kind.startswith("gap") and not self.read_only:
            entries.append((tr("Remove gap"),
                            lambda: self._write(service.remove_photo_gap, hit.id)))
        elif hit.kind == "strip" and not self.read_only:
            at = self.view.data.original_time(round(seconds))
            entries.append((tr("Insert gap here"), lambda: self._add_gap(at)))
        return entries

    def _open_menu(self, hit: Hit, seconds: float, where) -> None:
        entries = self.menu_entries(hit, seconds)
        if entries:
            menu = QMenu(self)
            for text, action in entries:
                menu.addAction(text, action)
            menu.exec(where)
