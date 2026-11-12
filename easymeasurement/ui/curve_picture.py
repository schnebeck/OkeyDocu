# EasyMeasurement - easymeasurement/ui/curve_picture.py
# A time-current characteristic drawn as a band, with the disconnecting current marked.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""`breaker <lower> <upper> [<no trip> <trip>]` describes a circuit breaker by the multiples of
its rated current: the instantaneous release trips between lower and upper, the thermal one
not within an hour at `no trip` and within an hour at `trip`. The band between the earliest
and the latest tripping is drawn on logarithmic axes, straight through the test points of
EN 60898-1 (an hour at the conventional currents, 1 s and 60 s at 2.55 × Iₙ) and falling with
the square of the current beyond. It shows the shape the limits give, not the curve of one
product.

The point marked is the disconnecting current Iₐ, the upper instantaneous limit, at the
disconnection time required."""
from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

from ..l10n import tr
from ..l10n.formats import pattern

X_RANGE = (1.0, 30.0)  # multiples of the rated current
T_RANGE = (0.005, 10_000.0)  # seconds
INSTANT_S = 0.01  # where an instantaneous release has broken the current
TEST_X = 2.55  # thermal test current, tripping between 1 s and 60 s
EARLIEST_AT_TEST_S, LATEST_AT_TEST_S = 1.0, 60.0
HOUR_S = 3600.0
SIZE = (380, 268)
MARGIN = (52, 22, 16, 36)  # left, top, right, bottom


@dataclass(frozen=True)
class Breaker:
    lower: float
    upper: float
    no_trip: float = 1.13
    trip: float = 1.45

    def thermal(self, x: float, latest: bool) -> float:
        """Seconds until the thermal release trips at the earliest or the latest."""
        k, at = (self.trip, LATEST_AT_TEST_S) if latest else (self.no_trip, EARLIEST_AT_TEST_S)
        if x <= k:
            return T_RANGE[1]
        if x >= TEST_X:
            return at * (TEST_X / x) ** 2
        slope = math.log(at / HOUR_S) / math.log(TEST_X / k)
        return HOUR_S * (x / k) ** slope

    def edge(self, latest: bool) -> list[tuple[float, float]]:
        """Points of the latest or the earliest tripping, from the top down to the instant."""
        start, magnetic = (self.trip, self.upper) if latest else (self.no_trip, self.lower)
        points, x = [(start, T_RANGE[1]), (start, HOUR_S)], start * 1.04
        while x < magnetic:
            points.append((x, self.thermal(x, latest)))
            x *= 1.04
        points.append((magnetic, self.thermal(magnetic, latest)))
        points += [(magnetic, INSTANT_S), (X_RANGE[1], INSTANT_S)]
        return points


def parse_curve(spec: str) -> Breaker | None:
    parts = spec.split()
    if not parts or parts[0] != "breaker":
        return None
    try:
        numbers = [float(part.replace(",", ".")) for part in parts[1:]]
    except ValueError:
        return None
    if len(numbers) not in (2, 4) or not 1 < numbers[0] < numbers[1]:
        return None
    return Breaker(*numbers)


def _number(value: float) -> str:
    return f"{value:g}".replace(".", pattern("decimal"))


class _Axes:
    def __init__(self, width: int, height: int):
        left, top, right, bottom = MARGIN
        self.area = QRectF(left, top, width - left - right, height - top - bottom)

    def at(self, x: float, t: float) -> QPointF:
        (x0, x1), (t0, t1) = X_RANGE, T_RANGE
        u = math.log(x / x0) / math.log(x1 / x0)
        v = math.log(max(min(t, t1), t0) / t0) / math.log(t1 / t0)
        return QPointF(self.area.left() + u * self.area.width(),
                       self.area.bottom() - v * self.area.height())


def curve_picture(breaker: Breaker, required_s: float = 0.4,
                  rated_a: float | None = None) -> QPixmap:
    """The band of the breaker and its disconnecting current at the required time; with a
    rated current the axis and the point also tell amperes."""
    ratio = QApplication.primaryScreen().devicePixelRatio() if QApplication.primaryScreen() else 1
    picture = QPixmap(int(SIZE[0] * ratio), int(SIZE[1] * ratio))
    picture.setDevicePixelRatio(ratio)
    palette = QApplication.palette()
    picture.fill(palette.color(QPalette.ColorRole.ToolTipBase))
    painter = QPainter(picture)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    axes = _Axes(*SIZE)
    ink = palette.color(QPalette.ColorRole.ToolTipText)
    _grid(painter, axes, ink, rated_a)
    band = QPainterPath(axes.at(*breaker.edge(True)[0]))
    for point in breaker.edge(True)[1:]:
        band.lineTo(axes.at(*point))
    for point in reversed(breaker.edge(False)):
        band.lineTo(axes.at(*point))
    band.closeSubpath()
    accent = QColor("#2e7dbf")
    fill = QColor(accent)
    fill.setAlpha(70)
    painter.fillPath(band, fill)
    painter.setPen(QPen(accent, 1.5))
    painter.drawPath(band)
    _mark(painter, axes, breaker.upper, required_s, rated_a)
    painter.end()
    return picture


def _grid(painter: QPainter, axes: _Axes, ink: QColor, rated_a: float | None) -> None:
    faint = QColor(ink)
    faint.setAlpha(50)
    font = painter.font()
    font.setPointSizeF(font.pointSizeF() * 0.8)
    painter.setFont(font)
    for x in (1, 2, 3, 5, 10, 20, 30):
        top, bottom = axes.at(x, T_RANGE[1]), axes.at(x, T_RANGE[0])
        painter.setPen(QPen(faint, 1))
        painter.drawLine(top, bottom)
        painter.setPen(ink)
        text = _number(x * rated_a) if rated_a else _number(x)
        painter.drawText(QRectF(bottom.x() - 20, bottom.y() + 2, 40, 14),
                         Qt.AlignmentFlag.AlignHCenter, text)
    for t in (0.01, 0.1, 1, 10, 100, 1000, 10_000):
        left, right = axes.at(X_RANGE[0], t), axes.at(X_RANGE[1], t)
        painter.setPen(QPen(faint, 1))
        painter.drawLine(left, right)
        painter.setPen(ink)
        painter.drawText(QRectF(0, left.y() - 7, MARGIN[0] - 6, 14),
                         Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                         _number(t) + " s")
    unit = "I / A" if rated_a else "I / Iₙ"
    painter.drawText(QRectF(axes.area.left(), axes.area.bottom() + 18, axes.area.width(), 14),
                     Qt.AlignmentFlag.AlignHCenter, unit)


def _mark(painter: QPainter, axes: _Axes, upper: float, required_s: float,
          rated_a: float | None) -> None:
    point = axes.at(upper, required_s)
    red = QColor("#c0392b")
    painter.setPen(QPen(red, 1, Qt.PenStyle.DashLine))
    painter.drawLine(axes.at(X_RANGE[0], required_s), point)
    painter.drawLine(point, axes.at(upper, T_RANGE[0]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(red)
    painter.drawEllipse(point, 4, 4)
    painter.setPen(red)
    current = (tr("{amperes} A", amperes=_number(upper * rated_a)) if rated_a
               else tr("{times} × Iₙ", times=_number(upper)))
    text = tr("Iₐ = {current} at {seconds} s", current=current, seconds=_number(required_s))
    painter.drawText(QRectF(point.x() + 6, point.y() - 18, 220, 16),
                     Qt.AlignmentFlag.AlignLeft, text)
