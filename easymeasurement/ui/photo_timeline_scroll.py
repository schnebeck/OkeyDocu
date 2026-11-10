# EasyMeasurement - easymeasurement/ui/photo_timeline_scroll.py
# A scroll bar along the time of the tracks, kept in step with zoom, pan and fitting.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QScrollBar

from .photo_timeline_model import FIT_LEFT_PX

TAIL_PX = 8  # beyond the widest thumbnail at the last moment


class TimelineScroll(QScrollBar):
    """Its units are pixels at the present zoom, counted from the left edge of the content.

    The range always takes in the present view as well, so a view zoomed or panned beyond
    the content does not jump back when the bar is touched.
    """

    def __init__(self, view, widest_ratio: float):
        super().__init__(Qt.Orientation.Horizontal)
        self.view = view
        self.widest_ratio = widest_ratio
        self._following = False
        self.valueChanged.connect(self._scrolled)
        view.axis_moved.connect(self.follow)
        self.setEnabled(False)

    def _content(self) -> tuple[float, float] | None:
        """The seconds from the left edge of the first thing to the right edge of the last."""
        content = self.view.data.content_range()
        if content is None:
            return None
        per_s = self.view.axis.px_per_s
        tail = self.view.tracks.thumb_height * self.widest_ratio + TAIL_PX
        return content[0] - FIT_LEFT_PX / per_s, content[1] + tail / per_s

    def follow(self) -> None:
        content = self._content()
        axis = self.view.axis
        self._following = True
        page = max(int(axis.width - axis.left), 1)
        value = whole = 0
        if content is not None:
            value = round((axis.seconds_at(axis.left) - content[0]) * axis.px_per_s)
            whole = round((content[1] - content[0]) * axis.px_per_s)
        if content is None or (value <= 0 and value + page >= whole):
            self.setRange(0, 0)  # everything is in view
        else:
            self.setRange(min(0, value), max(whole - page, value, 0))
            self.setPageStep(page)
            self.setSingleStep(max(page // 10, 1))
            self.setValue(value)
        self.setEnabled(self.maximum() > self.minimum())
        self._following = False

    def _scrolled(self, value: int) -> None:
        content = self._content()
        if self._following or content is None:
            return
        axis = self.view.axis
        axis.start = content[0] + value / axis.px_per_s - axis.left / axis.px_per_s
        self.view.fitted = False
        self.view.relayout()
