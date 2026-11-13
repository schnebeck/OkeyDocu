# OkeyDocu - okeydocu/ui/front_panel.py
# The instrument's front panel as drawn: a dial that turns and parts that light up.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The knob shows where the dial has to go and turns there; the position the instrument
reports is a ring around its label, green where it serves the measurement and red elsewhere.
Parts named in `point_at` pulse, so a guide can show the socket, key or detent that comes
next. A click on a detent asks for that position. `zoom_dial` moves in on the dial and back
out to the whole panel, `zoom_parts` in on other parts, such as display and softkeys."""

from __future__ import annotations

import math

from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..devices.guide import PanelDrawing

_POINT = QColor("#ff9f1c")
_MATCH = QColor("#3ec46d")
_ELSEWHERE = QColor("#e74c3c")
_TURN_MS = 700
_ZOOM_MS = 500
_ZOOM_MARGIN = 1.25  # of the dial's reach, around the dial when zoomed in
_PULSE_MS = 1100


class FrontPanel(QWidget):
    position_chosen = Signal(int)

    def __init__(self, drawing: PanelDrawing, parent=None):
        super().__init__(parent)
        self.drawing = drawing
        self.front = QSvgRenderer(str(drawing.front), self)
        self.knob = QSvgRenderer(str(drawing.knob), self)
        self.target: int | None = None
        self.actual: int | None = None
        self.fits: bool | None = None
        self.pointed: tuple[str, ...] = ()
        self.angle = 0.0
        self.pulse = 0.0
        self._turn = QVariantAnimation(self, duration=_TURN_MS)
        self._turn.setEasingCurve(QEasingCurve.Type.OutBack)
        self._turn.valueChanged.connect(self._turned)
        self._pulse = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=_PULSE_MS)
        self._pulse.setLoopCount(-1)
        self._pulse.valueChanged.connect(self._pulsed)
        self.view = self.front.viewBoxF()
        self._zoom = QVariantAnimation(self, duration=_ZOOM_MS)
        self._zoom.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self._zoom.valueChanged.connect(self._zoomed)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(472, 240)

    # What to show -------------------------------------------------------------

    def turn_to(self, value: int | None) -> None:
        """The knob turns the short way round to the detent the guide asks for."""
        self.target = value
        goal = self.drawing.angle_of(value) if value is not None else None
        if goal is None:
            self.update()
            return
        delta = (goal - self.angle + 180) % 360 - 180
        self._turn.stop()
        self._turn.setStartValue(self.angle)
        self._turn.setEndValue(self.angle + delta)
        self._turn.start()

    def show_actual(self, value: int | None, fits: bool | None = None) -> None:
        """`fits` says whether the reported position serves the measurement; by default only
        the target itself does."""
        self.actual = value
        self.fits = fits
        self.update()

    def zoom_dial(self, close: bool) -> None:
        """Close in on the dial, or show the whole panel again."""
        whole = self.front.viewBoxF()
        if close:
            reach = self.drawing.dial_reach * _ZOOM_MARGIN
            x, y = self.drawing.dial
            goal = QRectF(x - reach, y - reach, 2 * reach, 2 * reach)
        else:
            goal = whole
        self._zoom_to(goal)

    def zoom_parts(self, *ids: str) -> None:
        """Close in on the parts named, with some of the panel around them."""
        found = [self._bounds(i) for i in ids if self.front.elementExists(i)]
        if not found:
            self.zoom_dial(False)
            return
        goal = found[0]
        for bounds in found[1:]:
            goal = goal.united(bounds)
        margin = max(goal.width(), goal.height()) * (_ZOOM_MARGIN - 1)
        self._zoom_to(goal.adjusted(-margin, -margin, margin, margin))

    def _zoom_to(self, goal: QRectF) -> None:
        self._zoom.stop()
        self._zoom.setStartValue(QRectF(self.view))
        self._zoom.setEndValue(goal)
        self._zoom.start()

    def _zoomed(self, value) -> None:
        self.view = QRectF(value)
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
        """Scale and top left corner of the drawing, so the part in view fills the widget in
        proportion, centred."""
        view = self.view
        scale = min(self.width() / view.width(), self.height() / view.height())
        corner = QPointF((self.width() - view.width() * scale) / 2 - view.x() * scale,
                         (self.height() - view.height() * scale) / 2 - view.y() * scale)
        return scale, corner

    def _to_widget(self, rect: QRectF) -> QRectF:
        scale, corner = self._frame()
        return QRectF(corner.x() + rect.x() * scale, corner.y() + rect.y() * scale,
                      rect.width() * scale, rect.height() * scale)

    def _bounds(self, element: str) -> QRectF:
        """Where a part is in the drawing."""
        return self.front.transformForElement(element).mapRect(
            self.front.boundsOnElement(element))

    def part_rect(self, element: str) -> QRectF:
        """Where a part of the drawing is in the widget."""
        return self._to_widget(self._bounds(element))

    def _dial_centre(self) -> QPointF:
        return self._to_widget(QRectF(*self.drawing.dial, 0, 0)).topLeft()

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
        centre, radius = self._dial_centre(), self.drawing.knob_radius * scale
        painter.translate(centre)
        painter.rotate(self.angle)
        self.knob.render(painter, QRectF(-radius, -radius, 2 * radius, 2 * radius))

    def _paint_actual(self, painter: QPainter) -> None:
        if self.actual is None or not self.front.elementExists(f"pos-{self.actual}"):
            return
        rect = self.part_rect(f"pos-{self.actual}").adjusted(-6, -5, 6, 5)
        fits = self.actual == self.target if self.fits is None else self.fits
        color = _MATCH if fits else _ELSEWHERE
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
        if distance > self.drawing.dial_reach * scale or distance < 12 * scale:
            return
        degrees = math.degrees(math.atan2(offset.x(), -offset.y()))
        value = self.drawing.value_at(degrees)
        self.turn_to(value)
        self.position_chosen.emit(value)
