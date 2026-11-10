# EasyMeasurement - easymeasurement/ui/signature_pad.py
# A signature written with mouse or pen, or taken from a picture.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget

from ..l10n import tr

PAPER = QColor("white")
INK = QColor("#14213d")
GUIDE = QColor("#b8c0cc")
PEN_WIDTH = 2.2
EXPORT_SCALE = 3  # sharp in print
MAX_IMAGE_WIDTH = 900


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
        self.setMinimumSize(300, 110)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.strokes: list[QPainterPath] = []
        self.picture: QImage | None = None  # an existing signature, or one from a file

    @property
    def empty(self) -> bool:
        return self.picture is None and not self.strokes

    def clear(self) -> None:
        self.strokes.clear()
        self.picture = None
        self.update()
        self.changed.emit()

    def load(self, data: bytes | None) -> bool:
        image = QImage.fromData(data) if data else QImage()
        if image.isNull():
            return False
        if image.width() > MAX_IMAGE_WIDTH:
            image = image.scaledToWidth(
                MAX_IMAGE_WIDTH, Qt.TransformationMode.SmoothTransformation
            )
        self.strokes.clear()
        self.picture = image
        self.update()
        self.changed.emit()
        return True

    def data(self) -> bytes | None:
        """Cut to what was written, so it sits on the line and not somewhere above it."""
        if self.empty:
            return None
        if self.picture is not None and not self.strokes:
            return _png(self.picture)
        size = self.size() * EXPORT_SCALE
        image = QImage(size, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(EXPORT_SCALE, EXPORT_SCALE)
        self._draw(painter)
        painter.end()
        area = QRectF()
        for stroke in self.strokes:
            area = area.united(stroke.boundingRect())
        area = area.adjusted(-PEN_WIDTH, -PEN_WIDTH, PEN_WIDTH, PEN_WIDTH)
        scaled = QRectF(area.topLeft() * EXPORT_SCALE, area.size() * EXPORT_SCALE)
        return _png(image.copy(scaled.toAlignedRect()))

    def _draw(self, painter: QPainter) -> None:
        if self.picture is not None:
            target = QRectF(self.picture.rect())
            target.setSize(self.picture.size().scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio
            ).toSizeF())
            target.moveCenter(QRectF(self.rect()).center())
            painter.drawImage(target, self.picture)
        pen = QPen(INK, PEN_WIDTH)
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
        base = self.height() - 28
        painter.drawLine(16, base, self.width() - 16, base)
        if self.empty:
            painter.drawText(
                self.rect().adjusted(0, 0, 0, -32), Qt.AlignmentFlag.AlignCenter,
                tr("Sign here with mouse or pen"),
            )
        self._draw(painter)

    def mousePressEvent(self, event) -> None:
        if self.picture is not None:  # writing starts over, nothing is drawn across an old one
            self.picture = None
        stroke = QPainterPath(event.position())
        stroke.lineTo(event.position() + QPointF(0.1, 0.1))  # a dot is part of a name too
        self.strokes.append(stroke)
        self.update()

    def mouseMoveEvent(self, event) -> None:
        if self.strokes:
            self.strokes[-1].lineTo(event.position())
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        self.changed.emit()
