# EasyMeasurement - easymeasurement/ui/wiring_view.py
# Stylised, interactive wiring: instrument on the left, test object on the right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPainterPathStroker, QPen
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)

from ..campaign.plan import PlanStep
from ..l10n import tr

_DONE = QColor("#2e8b57")
_NEXT = QColor("#e67e22")
_LATER = QColor("#9aa5ae")
_PANEL = QColor("#2f3a44")
_OBJECT = QColor("#eef1f4")
_INK = QColor("#1f2933")
_PAPER = QColor("#ffffff")

WIDTH, HEIGHT = 760, 380
INSTRUMENT = QRectF(20, 30, 250, 320)
TEST_OBJECT = QRectF(520, 30, 220, 320)


class _Wire(QGraphicsPathItem):
    """A connection. It takes clicks on a broad band, not only on the thin line."""

    def __init__(self, path: QPainterPath, index: int, view: "WiringView"):
        super().__init__(path)
        self.index = index
        self.view = view
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAcceptHoverEvents(True)

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        stroker.setWidth(22)
        return stroker.createStroke(self.path())

    def mousePressEvent(self, event) -> None:
        # Wires can cross. Offer the click to every wire under the pointer, so
        # the one on top cannot swallow it.
        hits = [item.index for item in self.scene().items(event.scenePos())
                if isinstance(item, _Wire)]
        self.view.wires_clicked(hits)
        event.accept()


class WiringView(QGraphicsView):
    """Shows one step's setup. Connections are ticked off in the order given.

    Order matters: the plan puts PE first, and a click only ever advances to the
    next connection or takes back the last one.
    """

    progress = Signal(int, int)

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(0, 0, WIDTH, HEIGHT, self))
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setBackgroundBrush(QBrush(_PAPER))
        self.setMinimumHeight(180)
        self.step: PlanStep | None = None
        self.done = 0
        self.locked = False
        self.wires: list[_Wire] = []
        self.badges: list[tuple[QGraphicsEllipseItem, QGraphicsSimpleTextItem]] = []

    # Public --------------------------------------------------------------

    @property
    def total(self) -> int:
        return len(self.step.wiring.wires) if self.step else 0

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.done == self.total

    def show_step(self, step: PlanStep | None, connected: bool = False, locked: bool = False) -> None:
        self.step = step
        self.locked = locked
        self.done = self.total if connected else 0
        self._draw()
        self.progress.emit(self.done, self.total)

    def wire_clicked(self, index: int) -> None:
        self.wires_clicked([index])

    def wires_clicked(self, indices: list[int]) -> None:
        if self.locked:
            return
        if self.done in indices:
            self.done += 1
        elif self.done - 1 in indices:
            self.done -= 1
        else:
            return
        self._restyle()
        self.progress.emit(self.done, self.total)

    def _marker_position(self, index: int) -> float:
        """Spread the markers along their wires: crossing wires meet in the middle."""
        count = self.total
        return 0.5 if count < 2 else 0.28 + 0.44 * index / (count - 1)

    def wire_point(self, index: int) -> QPointF:
        """Where a connection's marker sits, in scene coordinates."""
        return self.wires[index].path().pointAtPercent(self._marker_position(index))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    # Drawing -------------------------------------------------------------

    def _text(self, text: str, x: float, y: float, size: int = 10, colour=_INK, bold=False,
              right: bool = False, centre: bool = False) -> QGraphicsSimpleTextItem:
        item = self.scene().addSimpleText(text)
        font = QFont()
        font.setPointSize(size)
        font.setBold(bold)
        item.setFont(font)
        item.setBrush(QBrush(colour))
        width = item.boundingRect().width()
        item.setPos(x - width if right else x - width / 2 if centre else x, y)
        return item

    def _draw(self) -> None:
        scene = self.scene()
        scene.clear()
        self.wires, self.badges = [], []
        if self.step is None:
            return
        wiring = self.step.wiring
        sockets = wiring.sockets or tuple(dict.fromkeys(w.socket for w in wiring.wires))
        used = {w.socket for w in wiring.wires}

        scene.addRect(INSTRUMENT, QPen(Qt.PenStyle.NoPen), QBrush(_PANEL))
        instrument = wiring.instrument or tr("Instrument")
        self._text(instrument, INSTRUMENT.left() + 16, 42, 11, _PAPER, True)
        scene.addRect(QRectF(36, 72, 158, 62), QPen(Qt.PenStyle.NoPen), QBrush(QColor("#d9e2d0")))
        self._text(tr("Selector switch"), 44, 78, 8)
        self._text(self.step.selector, 44, 98, 12, _INK, True)
        knob = QRectF(52, 186, 92, 92)
        scene.addEllipse(knob, QPen(QColor("#141a20"), 2), QBrush(QColor("#47535e")))
        scene.addLine(98, 232, 98, 194, QPen(_NEXT, 5))
        self._text(self.step.selector, 98, 286, 8, _PAPER, centre=True)

        socket_at: dict[str, QPointF] = {}
        spacing = INSTRUMENT.height() / (len(sockets) + 1)
        for index, socket in enumerate(sockets, 1):
            point = QPointF(INSTRUMENT.right() - 14, INSTRUMENT.top() + spacing * index)
            socket_at[socket] = point
            active = socket in used
            scene.addEllipse(
                QRectF(point.x() - 10, point.y() - 10, 20, 20),
                QPen(_PAPER if active else QColor("#6b7782"), 2),
                QBrush(QColor("#141a20")),
            )
            self._text(socket, point.x() - 16, point.y() - 8, 10,
                       _PAPER if active else QColor("#8a959f"), active, right=True)

        scene.addRect(TEST_OBJECT, QPen(_LATER, 1), QBrush(_OBJECT))
        title = self._text(wiring.object_label, TEST_OBJECT.left() + 14, 42, 10, _INK, True)
        if title.boundingRect().width() > TEST_OBJECT.width() - 24:
            title.setScale((TEST_OBJECT.width() - 24) / title.boundingRect().width())
        terminal_at: dict[str, QPointF] = {}
        spacing = (TEST_OBJECT.height() - 30) / (len(wiring.terminals) + 1)
        for index, terminal in enumerate(wiring.terminals, 1):
            point = QPointF(TEST_OBJECT.left() + 14, TEST_OBJECT.top() + 30 + spacing * index)
            terminal_at[terminal.id] = point
            scene.addRect(
                QRectF(point.x() - 7, point.y() - 7, 14, 14), QPen(_INK, 1.5), QBrush(_PAPER)
            )
            self._text(terminal.label, point.x() + 14, point.y() - 9, 10)

        for index, wire in enumerate(wiring.wires):
            start, end = socket_at[wire.socket], terminal_at[wire.target]
            path = QPainterPath(start)
            bend = (end.x() - start.x()) * 0.5
            path.cubicTo(start.x() + bend, start.y(), end.x() - bend, end.y(), end.x(), end.y())
            item = _Wire(path, index, self)
            scene.addItem(item)
            self.wires.append(item)
            middle = path.pointAtPercent(self._marker_position(index))
            badge = scene.addEllipse(QRectF(middle.x() - 13, middle.y() - 13, 26, 26))
            label = scene.addSimpleText("")
            badge.setZValue(2)
            label.setZValue(3)
            badge.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
            self.badges.append((badge, label))
        self._restyle()
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _restyle(self) -> None:
        for index, wire in enumerate(self.wires):
            if index < self.done:
                colour, style, text = _DONE, Qt.PenStyle.SolidLine, "✓"
            elif index == self.done:
                colour, style, text = _NEXT, Qt.PenStyle.SolidLine, str(index + 1)
            else:
                colour, style, text = _LATER, Qt.PenStyle.DashLine, str(index + 1)
            wire.setPen(QPen(colour, 4, style, Qt.PenCapStyle.RoundCap))
            badge, label = self.badges[index]
            badge.setPen(QPen(Qt.PenStyle.NoPen))
            badge.setBrush(QBrush(colour))
            label.setText(text)
            font = QFont()
            font.setBold(True)
            label.setFont(font)
            label.setBrush(QBrush(_PAPER))
            middle = self.wire_point(index)
            box = label.boundingRect()
            label.setPos(middle.x() - box.width() / 2, middle.y() - box.height() / 2)
