# OkeyDocu - okeydocu/ui/logo_placer.py
# A miniature page: drag the logo to place it, drag its corner to scale it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..l10n import tr
from ..reporting.logo import MARGIN_MM, PAGE_HEIGHT_MM, PAGE_WIDTH_MM, clamp_placement

_HANDLE_PX = 12
_PAGE_PX_HEIGHT = 340


class LogoPlacer(QWidget):
    placementChanged = Signal(float, float, float)  # x, y, width in mm

    def __init__(self):
        super().__init__()
        self.pixmap = QPixmap()
        self.ratio = 1.0
        self.x_mm = self.y_mm = 0.0
        self.width_mm = 40.0
        self._mode = ""
        self._grab = QPointF()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip(tr("Drag the logo to move it, drag the corner to scale it"))

    @property
    def scale(self) -> float:
        return _PAGE_PX_HEIGHT / PAGE_HEIGHT_MM

    def sizeHint(self) -> QSize:
        return QSize(round(PAGE_WIDTH_MM * self.scale) + 2, _PAGE_PX_HEIGHT + 2)

    def set_logo(self, pixmap: QPixmap, ratio: float) -> None:
        self.pixmap = pixmap
        self.ratio = ratio
        self.update()

    def set_placement(self, x: float, y: float, width: float) -> None:
        self.x_mm, self.y_mm, self.width_mm = clamp_placement(x, y, width, self.ratio)
        self.update()

    def logo_rect(self) -> QRectF:
        s = self.scale
        return QRectF(
            self.x_mm * s + 1, self.y_mm * s + 1, self.width_mm * s, self.width_mm * self.ratio * s
        )

    def _handle(self) -> QRectF:
        corner = self.logo_rect().bottomRight()
        return QRectF(corner.x() - _HANDLE_PX / 2, corner.y() - _HANDLE_PX / 2,
                      _HANDLE_PX, _HANDLE_PX)

    def paintEvent(self, _) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        s = self.scale
        page = QRectF(1, 1, PAGE_WIDTH_MM * s, PAGE_HEIGHT_MM * s)
        painter.fillRect(page, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#8a959f"), 1))
        painter.drawRect(page)
        painter.setPen(QPen(QColor("#c8ced6"), 1, Qt.PenStyle.DashLine))
        painter.drawRect(page.adjusted(MARGIN_MM * s, MARGIN_MM * s, -MARGIN_MM * s, -MARGIN_MM * s))
        rect = self.logo_rect()
        if not self.pixmap.isNull():
            painter.drawPixmap(rect, self.pixmap, QRectF(self.pixmap.rect()))
        painter.setPen(QPen(QColor("#e67e22"), 1))
        painter.drawRect(rect)
        painter.fillRect(self._handle(), QColor("#e67e22"))

    def mousePressEvent(self, event) -> None:
        position = event.position()
        if self._handle().contains(position):
            self._mode = "scale"
        elif self.logo_rect().contains(position):
            self._mode = "move"
            self._grab = position - self.logo_rect().topLeft()
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        position = event.position()
        if not self._mode:
            over_handle = self._handle().contains(position)
            over_logo = self.logo_rect().contains(position)
            self.setCursor(
                Qt.CursorShape.SizeFDiagCursor if over_handle
                else Qt.CursorShape.SizeAllCursor if over_logo
                else Qt.CursorShape.ArrowCursor
            )
            return
        s = self.scale
        if self._mode == "move":
            corner = position - self._grab
            placed = ((corner.x() - 1) / s, (corner.y() - 1) / s, self.width_mm)
        else:
            width = (position.x() - self.logo_rect().left()) / s
            placed = (self.x_mm, self.y_mm, width)
        self.x_mm, self.y_mm, self.width_mm = clamp_placement(*placed, self.ratio)
        self.update()
        self.placementChanged.emit(self.x_mm, self.y_mm, self.width_mm)

    def mouseReleaseEvent(self, event) -> None:
        self._mode = ""
        event.accept()
