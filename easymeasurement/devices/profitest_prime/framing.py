# EasyMeasurement - easymeasurement/devices/profitest_prime/framing.py
# Cuts the instrument's byte stream into replies, events and text lines.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import re

REPLY = "reply"
EVENT = "event"
TEXT = "text"

_MARKERS = ((b"</reply>", b"<reply>", REPLY), (b"</Event>", b"<Event ", EVENT))
# Commands without an XML form answer with one line: a code, then `;` and the data.
_TEXT_RE = re.compile(rb"\s*(-?\d+(?:;[^<\r\n]*)?)\r?\n")


class FrameSplitter:
    """Cuts the byte stream into frames, in order.

    Every frame that arrives comes out, however the stream was chopped up: an
    event is a measurement that exists nowhere else. Frames start with `<`, so a
    text line is only recognised at the start of the buffer, never inside a frame.
    """

    def __init__(self) -> None:
        self._buffer = b""

    def feed(self, data: bytes) -> list[tuple[str, bytes]]:
        self._buffer += data
        frames = []
        while True:
            line = _TEXT_RE.match(self._buffer)
            if line:
                frames.append((TEXT, line[1]))
                self._buffer = self._buffer[line.end():]
                continue
            ends = [
                (index, marker, opening, kind)
                for marker, opening, kind in _MARKERS
                if (index := self._buffer.find(marker)) >= 0
            ]
            if not ends:
                return frames
            index, marker, opening, kind = min(ends)
            end = index + len(marker)
            # "<Event " with a space: "<Event" alone also matches the inner <EventArgs>.
            start = max(self._buffer.rfind(opening, 0, index), 0)
            frames.append((kind, self._buffer[start:end]))
            head = self._buffer[:start]
            unfinished = b"<reply>" in head or b"<Event " in head
            self._buffer = (head if unfinished else b"") + self._buffer[end:].lstrip(b"\r\n")
