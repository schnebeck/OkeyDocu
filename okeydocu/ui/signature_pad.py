# OkeyDocu - okeydocu/ui/signature_pad.py
# A signature written with mouse or pen, or taken from a picture, set on its line.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The pad stands for the line of a report that is signed on. Whatever is written or loaded
lives in a box of fixed shape whose line lies at `BASELINE` of its height; the report puts
that line on its own, so a signature sits there as it sat here, its descenders below. In
aligning mode a drag moves the signature and the wheel makes it larger or smaller."""
from __future__ import annotations

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen, QTransform
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..l10n import tr

PAPER = QColor("white")
INK = QColor("#14213d")
GUIDE = QColor("#b8c0cc")
BOX = QSize(1200, 300)  # the stored picture: four times as wide as high
BASELINE = 0.75  # where the line lies, as a part of the height; the report reads it from here
BASELINE_KEY = "baseline"
PEN = 6.0  # in pixels of the box
STEP = 1.1  # one notch of the wheel


def _png(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


class SignaturePad(QWidget):
    """White like the paper it ends up on, also in a dark theme."""

    changed = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(320, 80)
        policy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        policy.setHeightForWidth(True)
        self.setSizePolicy(policy)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.strokes: list[QPainterPath] = []  # in pixels of the box
        self.picture: QImage | None = None  # an existing signature, or one from a file
        self.place = QRectF()  # where the picture stands in the box
        self.aligning = False
        self._grab: QPointF | None = None
        self._stored: bytes | None = None  # as loaded, kept until something is changed

    def heightForWidth(self, width: int) -> int:
        return width * BOX.height() // BOX.width()

    @property
    def empty(self) -> bool:
        return self.picture is None and not self.strokes

    def clear(self) -> None:
        self.strokes.clear()
        self.picture = None
        self._stored = None
        self.update()
        self.changed.emit()

    # The box on screen ---------------------------------------------------------------

    def _to_screen(self) -> QTransform:
        scale = self.width() / BOX.width()
        top = (self.height() - BOX.height() * scale) / 2
        return QTransform().translate(0, top).scale(scale, scale)

    def _in_box(self, point: QPointF) -> QPointF:
        return self._to_screen().inverted()[0].map(point)

    # Loading and storing -------------------------------------------------------------

    def load(self, data: bytes | None) -> bool:
        """A picture written on this pad keeps its place; any other one is set on the line,
        as large as a signature usually is."""
        image = QImage.fromData(data) if data else QImage()
        if image.isNull():
            return False
        if image.text(BASELINE_KEY):
            place = QRectF(0, 0, BOX.width(), BOX.height())
        else:
            line = BOX.height() * BASELINE
            size = image.size().scaled(QSize(int(BOX.width() * 0.8), int(line * 0.85)),
                                       Qt.AspectRatioMode.KeepAspectRatio)
            place = QRectF(BOX.width() * 0.05, line - size.height(), size.width(), size.height())
        self.strokes.clear()
        self.picture, self.place, self._stored = image, place, data
        self.update()
        self.changed.emit()
        return True

    def _rendered(self) -> QImage:
        image = QImage(BOX, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw(painter)
        painter.end()
        return image

    def data(self) -> bytes | None:
        """The whole box with the line's place written into it, so the report can set it on
        its line."""
        if self.empty:
            return None
        if self._stored is not None:
            return self._stored
        image = self._rendered()
        image.setText(BASELINE_KEY, str(BASELINE))
        return _png(image)

    def set_aligning(self, on: bool) -> None:
        """Strokes become one picture first, so they move and grow together."""
        if on and self.strokes:
            self.picture = self._rendered()
            self.place = QRectF(0, 0, BOX.width(), BOX.height())
            self.strokes.clear()
        self.aligning = on
        cursor = Qt.CursorShape.OpenHandCursor if on else Qt.CursorShape.CrossCursor
        self.setCursor(cursor)

    # Drawing -------------------------------------------------------------------------

    def _draw(self, painter: QPainter) -> None:
        if self.picture is not None:
            painter.drawImage(self.place, self.picture)
        pen = QPen(INK, PEN)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        for stroke in self.strokes:
            painter.drawPath(stroke)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), PAPER)
        painter.setPen(QPen(GUIDE, 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        transform = self._to_screen()
        base = transform.map(QPointF(0, BOX.height() * BASELINE)).y()
        painter.drawLine(QPointF(16, base), QPointF(self.width() - 16, base))
        if self.empty:
            painter.drawText(QRectF(0, 0, self.width(), base - 4), Qt.AlignmentFlag.AlignCenter,
                             tr("Sign here with mouse or pen"))
        painter.setTransform(transform)
        self._draw(painter)

    # Mouse and wheel -----------------------------------------------------------------

    def mousePressEvent(self, event) -> None:
        point = self._in_box(event.position())
        self._stored = None
        if self.aligning:
            self._grab = point if self.picture is not None else None
            return
        if self.picture is not None:  # writing starts over, nothing is drawn across an old one
            self.picture = None
        stroke = QPainterPath(point)
        stroke.lineTo(point + QPointF(0.3, 0.3))  # a dot is part of a name too
        self.strokes.append(stroke)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        point = self._in_box(event.position())
        if self.aligning and self._grab is not None:
            self.place.translate(point - self._grab)
            self._grab = point
            self.update()
        elif not self.aligning and self.strokes:
            self.strokes[-1].lineTo(point)
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        self._grab = None
        self.changed.emit()

    def wheelEvent(self, event) -> None:
        if not (self.aligning and self.picture is not None):
            return super().wheelEvent(event)
        self._stored = None
        factor = STEP ** (event.angleDelta().y() / 120)
        centre = self._in_box(event.position())
        place = self.place
        self.place = QRectF(centre.x() - (centre.x() - place.x()) * factor,
                            centre.y() - (centre.y() - place.y()) * factor,
                            place.width() * factor, place.height() * factor)
        self.update()
        self.changed.emit()
