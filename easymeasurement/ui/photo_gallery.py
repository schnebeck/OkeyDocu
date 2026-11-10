# EasyMeasurement - easymeasurement/ui/photo_gallery.py
# The photos of the chosen measurement; one dragged onto another row belongs there instead.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QEvent, QModelIndex, QPointF, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QListWidget,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QToolTip,
)

from ..l10n import N_, tr
from .photo_shared import start_photo_drag

PHOTO_PATH = Qt.ItemDataRole.UserRole + 1
PHOTO_ID = Qt.ItemDataRole.UserRole + 2
CROSS_PX = 22
CROSS_TIP = N_("Detach from this measurement: the photo goes to the unassigned photos.")
HOVER = QColor("#e74c3c")


class _CrossDelegate(QStyledItemDelegate):
    """Paints the item as usual, then a round cross on the picture's upper right corner."""

    def paint(self, painter: QPainter, option, index: QModelIndex) -> None:
        super().paint(painter, option, index)
        view = self.parent()
        if not view.removable:
            return
        box = view.cross_rect(index)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(HOVER if index == view.hovered else QColor(0, 0, 0, 150))
        painter.drawEllipse(box)
        pen = QPen(QColor("white"), 2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        inner = box.adjusted(7, 7, -7, -7)
        painter.drawLine(QPointF(inner.topLeft()), QPointF(inner.bottomRight()) + QPointF(1, 1))
        painter.drawLine(QPointF(inner.topRight()) + QPointF(1, 0),
                         QPointF(inner.bottomLeft()) + QPointF(0, 1))
        painter.restore()


class PhotoGallery(QListWidget):
    """Thumbnails in a grid. Dragging one carries the photo, not a copy of the item."""

    unpinned = Signal(int)  # the photo whose cross was clicked

    def __init__(self, thumb: int):
        super().__init__()
        self.removable = False
        self.hovered = QModelIndex()
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QPixmap(thumb, thumb).size())
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setMovement(QListWidget.Movement.Static)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        self.setItemDelegate(_CrossDelegate(self))
        self.setMouseTracking(True)
        self.setToolTip(tr("Double-click shows the photo large; dragged onto another row of"
                           " the table, it belongs to that measurement."))

    def cross_rect(self, index: QModelIndex) -> QRect:
        """The picture's own corner: a landscape photo leaves the icon square partly empty."""
        option = QStyleOptionViewItem()
        self.initViewItemOption(option)
        option.rect = self.visualRect(index)
        self.itemDelegate().initStyleOption(option, index)
        square = self.style().subElementRect(
            QStyle.SubElement.SE_ItemViewItemDecoration, option, self)
        picture = QStyle.alignedRect(
            Qt.LayoutDirection.LeftToRight, Qt.AlignmentFlag.AlignCenter,
            option.icon.actualSize(self.iconSize()), square)
        return QRect(picture.right() - CROSS_PX - 3, picture.top() + 3, CROSS_PX, CROSS_PX)

    def cross_at(self, point) -> QModelIndex:
        index = self.indexAt(point)
        if self.removable and index.isValid() and self.cross_rect(index).contains(point):
            return index
        return QModelIndex()

    def mousePressEvent(self, event) -> None:
        index = self.cross_at(event.position().toPoint())
        if index.isValid() and event.button() == Qt.MouseButton.LeftButton:
            self.hovered = QModelIndex()
            self.unpinned.emit(self.itemFromIndex(index).data(PHOTO_ID))
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """The second click of a quick double click must not take the next photo along."""
        if not self.cross_at(event.position().toPoint()).isValid():
            super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event) -> None:
        index = self.cross_at(event.position().toPoint())
        if index != self.hovered:
            self.hovered = index
            self.viewport().update()
        super().mouseMoveEvent(event)

    def viewportEvent(self, event) -> bool:
        if event.type() == QEvent.Type.ToolTip and self.cross_at(event.pos()).isValid():
            QToolTip.showText(event.globalPos(), tr(CROSS_TIP), self)
            return True
        if event.type() == QEvent.Type.Leave and self.hovered.isValid():
            self.hovered = QModelIndex()
            self.viewport().update()
        return super().viewportEvent(event)

    def startDrag(self, actions) -> None:
        item = self.currentItem()
        if item is not None and item.data(PHOTO_ID) is not None:
            start_photo_drag(self, item.data(PHOTO_ID), item.icon().pixmap(self.iconSize()))
