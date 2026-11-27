# OkeyDocu - okeydocu/devices/climate/settling.py
# Whether a sensor laid out at the place of the test has taken on the air around it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A sensor brought from a warm pocket into a cool hall needs minutes to follow the air. It
counts as settled once its temperature has moved by less than a tenth of a degree for a minute;
until then it is still on its way, and the reading would tell of the pocket."""

from __future__ import annotations

from collections import deque

SPAN_S, STEP_K = 60.0, 0.1
KEPT = 600  # readings remembered, as a bound


class Settling:
    def __init__(self, span_s: float = SPAN_S, step_k: float = STEP_K):
        self.span_s, self.step_k = span_s, step_k
        self._seen: deque[tuple[float, float]] = deque(maxlen=KEPT)

    def add(self, moment: float, temperature: float) -> None:
        self._seen.append((moment, temperature))
        while self._seen and self._seen[0][0] < moment - 2 * self.span_s:
            self._seen.popleft()

    def restart(self) -> None:
        self._seen.clear()

    def settled(self, now: float) -> bool:
        """Readings over a whole span, all within a tenth of a degree of each other."""
        recent = [value for moment, value in self._seen if moment >= now - self.span_s]
        covered = bool(self._seen) and self._seen[0][0] <= now - self.span_s
        return covered and bool(recent) and max(recent) - min(recent) < self.step_k

    def left_s(self, now: float) -> float:
        """Seconds of steady readings still missing, 0 once settled."""
        if self.settled(now) or not self._seen:
            return 0.0 if self._seen else self.span_s
        values = list(self._seen)
        start = values[-1][0]
        for moment, value in reversed(values):
            if abs(value - values[-1][1]) >= self.step_k:
                break
            start = moment
        return max(0.0, self.span_s - (now - start))
