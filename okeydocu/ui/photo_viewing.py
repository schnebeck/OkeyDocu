# OkeyDocu - okeydocu/ui/photo_viewing.py
# Turning a photo and cutting it to the part that matters, in the large photo view.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The original stays as it was taken; the view is stored beside it and every picture of the
photo, in the report, the gallery and here, is shown through it. Marks move along with the
view, so they keep pointing at the same spot."""
from __future__ import annotations

from PySide6.QtCore import QRect, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QImage, QPixmap, QTransform
from PySide6.QtWidgets import QHBoxLayout, QToolButton

from ..campaign.photo_view import PhotoView, move_mark
from ..l10n import tr


def viewed(image: QImage, view: PhotoView | None) -> QImage:
    """The picture turned and cut as the view says."""
    if view is None or view.plain:
        return image
    if view.rotation:
        image = image.transformed(QTransform().rotate(view.rotation))
    x, y, w, h = view.crop
    box = QRect(round(x * image.width()), round(y * image.height()),
                round(w * image.width()), round(h * image.height()))
    return image.copy(box)


def fitted(image: QImage, room: QSize) -> QPixmap:
    if image.width() > room.width() or image.height() > room.height():
        image = image.scaled(room, Qt.AspectRatioMode.KeepAspectRatio,
                             Qt.TransformationMode.SmoothTransformation)
    return QPixmap.fromImage(image)


class PhotoViewing:
    """Needs `canvas`, `source` (the upright picture), `room`, `view` and `editable`."""

    def _view_tools(self) -> QHBoxLayout:
        row = QHBoxLayout()
        self.turn_left = self._tool(tr("Turn left"), "object-rotate-left", lambda: self._turn(-1))
        self.turn_right = self._tool(tr("Turn right"), "object-rotate-right",
                                     lambda: self._turn(1))
        self.cut_button = self._tool(tr("Cut out …"), "transform-crop", lambda: None)
        self.cut_button.setCheckable(True)
        self.cut_button.setToolTip(tr("Drag a rectangle across the photo: only that part stays"
                                      " in view and in the report."))
        self.whole_button = self._tool(tr("Whole photo"), "zoom-fit-best", self._whole)
        for button in (self.turn_left, self.turn_right, self.cut_button, self.whole_button):
            row.addWidget(button)
        row.addStretch(1)
        self._update_tools()
        return row

    def _tool(self, text: str, icon: str, slot) -> QToolButton:
        button = QToolButton(text=text)
        button.setIcon(QIcon.fromTheme(icon))
        button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        button.setAutoRaise(True)
        button.setEnabled(self.editable)
        button.clicked.connect(lambda _=False: slot())
        return button

    def _update_tools(self) -> None:
        self.whole_button.setEnabled(self.editable and self.view.crop != PhotoView().crop)

    @property
    def cutting(self) -> bool:
        return self.cut_button.isChecked()

    def _change_view(self, view: PhotoView) -> None:
        """Shows the new view and carries the marks over to it."""
        moved = [move_mark(mark, self.view, view) for mark in self.marks()]
        self.canvas.marks = [mark for mark in moved if mark is not None]
        self.view = view
        self.canvas.pixmap = fitted(viewed(self.source, view), self.room)
        self.canvas.updateGeometry()
        self.canvas.update()
        self._fill()
        self._update_tools()

    def _turn(self, quarter: int) -> None:
        self._change_view(self.view.turned(quarter))

    def _cut(self, box: QRectF) -> None:
        self.cut_button.setChecked(False)
        self._change_view(self.view.cut((box.x(), box.y(), box.width(), box.height())))

    def _whole(self) -> None:
        self._change_view(self.view.whole())
