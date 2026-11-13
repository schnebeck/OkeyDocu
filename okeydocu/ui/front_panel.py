# OkeyDocu - okeydocu/ui/front_panel.py
# The instrument's front panel as drawn: a dial that turns and parts that light up.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The knob shows where the dial has to go and turns there; the position the instrument
reports is a ring around its label, green where it matches and red elsewhere. Parts named in `point_at` pulse,
so a guide can show the socket, key or detent that comes next. A click on a detent asks for
that position."""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..devices.profitest_prime import panel

_POINT = QColor("#ff9f1c")
_MATCH = QColor("#3ec46d")
_ELSEWHERE = QColor("#e74c3c")
_TURN_MS = 700
_PULSE_MS = 1100


class FrontPanel(QWidget):
    position_chosen = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.front = QSvgRenderer(str(panel.FRONT), self)
        self.knob = QSvgRenderer(str(panel.KNOB), self)
        self.target: int | None = None
        self.actual: int | None = None
        self.pointed: tuple[str, ...] = ()
        self.angle = 0.0
        self.pulse = 0.0
        self._turn = QVariantAnimation(self, duration=_TURN_MS)
        self._turn.setEasingCurve(QEasingCurve.Type.OutBack)
        self._turn.valueChanged.connect(self._turned)
        self._pulse = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=_PULSE_MS)
        self._pulse.setLoopCount(-1)
        self._pulse.valueChanged.connect(self._pulsed)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(472, 240)

    # What to show -------------------------------------------------------------

    def turn_to(self, value: int | None) -> None:
        """The knob turns the short way round to the detent the guide asks for."""
        self.target = value
        goal = panel.angle_of(value) if value is not None else None
        if goal is None:
            self.update()
            return
        delta = (goal - self.angle + 180) % 360 - 180
        self._turn.stop()
        self._turn.setStartValue(self.angle)
        self._turn.setEndValue(self.angle + delta)
        self._turn.start()

    def show_actual(self, value: int | None) -> None:
        self.actual = value
        self.update()

    def point_at(self, *ids: str) -> None:
        self.pointed = tuple(i for i in ids if self.front.elementExists(i))
        if self.pointed:
            self._pulse.start()
        else:
            self._pulse.stop()
        self.update()

    # Geometry -----------------------------------------------------------------

    def _frame(self) -> tuple[float, QPointF]:
        """Scale and top left corner of the drawing, kept in proportion and centred."""
        box = self.front.viewBoxF()
        scale = min(self.width() / box.width(), self.height() / box.height())
        corner = QPointF((self.width() - box.width() * scale) / 2,
                         (self.height() - box.height() * scale) / 2)
        return scale, corner

    def _to_widget(self, rect: QRectF) -> QRectF:
        scale, corner = self._frame()
        return QRectF(corner.x() + rect.x() * scale, corner.y() + rect.y() * scale,
                      rect.width() * scale, rect.height() * scale)

    def part_rect(self, element: str) -> QRectF:
        """Where a part of the drawing is in the widget."""
        bounds = self.front.transformForElement(element).mapRect(
            self.front.boundsOnElement(element))
        return self._to_widget(bounds)

    def _dial_centre(self) -> QPointF:
        return self._to_widget(QRectF(*panel.DIAL, 0, 0)).topLeft()

    # Drawing ------------------------------------------------------------------

    def _turned(self, value) -> None:
        self.angle = float(value)
        self.update()

    def _pulsed(self, value) -> None:
        self.pulse = float(value)
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale, corner = self._frame()
        box = self.front.viewBoxF()
        self.front.render(painter, QRectF(corner.x(), corner.y(), box.width() * scale,
                                          box.height() * scale))
        self._paint_actual(painter)
        self._paint_pointed(painter)
        centre, radius = self._dial_centre(), panel.KNOB_RADIUS * scale
        painter.translate(centre)
        painter.rotate(self.angle)
        self.knob.render(painter, QRectF(-radius, -radius, 2 * radius, 2 * radius))

    def _paint_actual(self, painter: QPainter) -> None:
        if self.actual is None or not self.front.elementExists(f"pos-{self.actual}"):
            return
        rect = self.part_rect(f"pos-{self.actual}").adjusted(-6, -5, 6, 5)
        color = _MATCH if self.actual == self.target else _ELSEWHERE
        painter.setPen(QPen(color, 2.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 6, 6)

    def _paint_pointed(self, painter: QPainter) -> None:
        glow = QColor(_POINT)
        glow.setAlphaF(0.35 + 0.65 * (1 - abs(2 * self.pulse - 1)))
        painter.setPen(QPen(glow, 3 + 3 * self.pulse))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for element in self.pointed:
            rect = self.part_rect(element)
            grow = 4 + 6 * self.pulse
            painter.drawRoundedRect(rect.adjusted(-grow, -grow, grow, grow), 8, 8)

    # Choosing a position ------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        scale, _ = self._frame()
        offset = event.position() - self._dial_centre()
        distance = math.hypot(offset.x(), offset.y())
        if distance > 190 * scale or distance < 20 * scale:
            return
        degrees = math.degrees(math.atan2(offset.x(), -offset.y()))
        value = panel.value_at(degrees)
        self.turn_to(value)
        self.position_chosen.emit(value)
