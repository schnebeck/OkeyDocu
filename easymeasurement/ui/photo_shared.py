# EasyMeasurement - easymeasurement/ui/photo_shared.py
# What all photo widgets share: cached thumbnails and carrying a photo by drag and drop.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import time
from collections import deque
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QByteArray, QEvent, QMimeData, QObject, QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QDrag, QImageReader, QPainter, QPixmap
from PySide6.QtWidgets import QWidget

from ..campaign.photo_proxies import fresh_proxy

PHOTO_MIME = "application/x-easymeasurement-photo"
DRAG_IMAGE_PX = 72
THUMB_EDGE_PX = 192  # longest edge: sharp on a high-resolution screen too
SLICE_S = 0.012  # decoding gives way to events after this long
MAX_KEPT = 1000  # about 100 MB of thumbnails, several full campaigns


# Thumbnails ------------------------------------------------------------------


def missing_picture() -> QPixmap:
    """Stands in for a file that cannot be read."""
    pixmap = QPixmap(THUMB_EDGE_PX, THUMB_EDGE_PX * 3 // 4)
    pixmap.fill(QColor("#8a8f96"))
    painter = QPainter(pixmap)
    font = painter.font()
    font.setPixelSize(pixmap.height() // 2)
    painter.setFont(font)
    painter.setPen(QColor("white"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "?")
    painter.end()
    return pixmap


def read_thumbnail(path: str) -> QPixmap:
    """Decode at the small size directly and honour the rotation stored in the file.
    A fresh proxy is read instead of the original: it is upright already and far smaller."""
    proxy = fresh_proxy(Path(path))
    reader = QImageReader(str(proxy) if proxy else path)
    reader.setAutoTransform(True)
    size = reader.size()
    if size.isValid() and max(size.width(), size.height()) > THUMB_EDGE_PX:
        reader.setScaledSize(size.scaled(
            THUMB_EDGE_PX, THUMB_EDGE_PX, Qt.AspectRatioMode.KeepAspectRatio
        ))
    image = reader.read()
    return QPixmap.fromImage(image) if not image.isNull() else missing_picture()


class ThumbCache(QObject):
    """Answers at once from memory; a file not read yet arrives later through `ready`.

    The file names of campaign photos carry their content hash, so a path never
    changes its picture.
    """

    ready = Signal(str)

    def __init__(self):
        super().__init__()
        self._pixmaps: dict[str, QPixmap] = {}
        self._waiting: deque[str] = deque()
        self._paused = False
        self._timer = QTimer(self, singleShot=True, interval=0)
        self._timer.timeout.connect(self._read_slice)

    def get(self, path: Path) -> QPixmap | None:
        key = str(path)
        known = self._pixmaps.get(key)
        if known is None and key not in self._waiting:
            self._waiting.append(key)
            self._timer.start()
        return known

    def pause(self, paused: bool) -> None:
        """A held gesture goes first: one large file takes longer than a frame."""
        self._paused = paused
        if not paused and self._waiting:
            self._timer.start()

    def finish(self) -> None:
        """Read everything still waiting, without giving way to events."""
        while self._waiting:
            self._read_next()

    def _read_next(self) -> None:
        key = self._waiting.popleft()
        self._pixmaps[key] = read_thumbnail(key)
        if len(self._pixmaps) > MAX_KEPT:
            del self._pixmaps[next(iter(self._pixmaps))]  # the one read longest ago
        self.ready.emit(key)

    def _read_slice(self) -> None:
        if self._paused:
            return
        deadline = time.monotonic() + SLICE_S
        while self._waiting and time.monotonic() < deadline:
            self._read_next()
        if self._waiting:
            self._timer.start()


_shared: ThumbCache | None = None


def shared_thumbs() -> ThumbCache:
    """One cache for the timeline and the stack, so no file is decoded twice."""
    global _shared
    if _shared is None:
        _shared = ThumbCache()
    return _shared


# Drag and drop ---------------------------------------------------------------


def photo_mime_data(photo_id: int) -> QMimeData:
    data = QMimeData()
    data.setData(PHOTO_MIME, QByteArray(str(photo_id).encode()))
    return data


def dropped_photo(mime: QMimeData) -> int | None:
    """The photo id a drag carries, or None when it carries something else."""
    if not mime.hasFormat(PHOTO_MIME):
        return None
    text = bytes(mime.data(PHOTO_MIME)).decode()
    return int(text) if text.isdecimal() else None


def start_photo_drag(source: QWidget, photo_id: int, pixmap: QPixmap | None = None) -> None:
    """Carry a photo with its picture under the pointer until it is dropped."""
    drag = QDrag(source)
    drag.setMimeData(photo_mime_data(photo_id))
    if pixmap is not None and not pixmap.isNull():
        shown = pixmap.scaled(
            DRAG_IMAGE_PX, DRAG_IMAGE_PX, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(shown)
        drag.setHotSpot(QPoint(shown.width() // 2, shown.height() // 2))
    drag.exec(Qt.DropAction.MoveAction)


class PhotoDropTarget(QObject):
    """Lets any widget take a dropped photo. `allowed` may refuse a position while the
    drag passes over it, `enabled` switches the whole target off."""

    def __init__(self, widget: QWidget, on_drop: Callable[[int, QPoint], None],
                 allowed: Callable[[QPoint], bool] | None = None):
        super().__init__(widget)
        self.on_drop = on_drop
        self.allowed = allowed
        self.enabled = True
        widget.setAcceptDrops(True)
        widget.installEventFilter(self)

    def _wanted(self, event) -> bool:
        if not self.enabled or dropped_photo(event.mimeData()) is None:
            return False
        return self.allowed is None or self.allowed(event.position().toPoint())

    def eventFilter(self, watched, event) -> bool:
        kind = event.type()
        if kind not in (QEvent.Type.DragEnter, QEvent.Type.DragMove, QEvent.Type.Drop):
            return False
        if not self._wanted(event):
            event.ignore()
            return True
        event.setDropAction(Qt.DropAction.MoveAction)
        event.accept()
        if kind == QEvent.Type.Drop:
            self.on_drop(dropped_photo(event.mimeData()), event.position().toPoint())
        return True


def accept_photo_drops(widget: QWidget, on_drop: Callable[[int, QPoint], None],
                       allowed: Callable[[QPoint], bool] | None = None) -> PhotoDropTarget:
    """For a table pass its viewport: `on_drop(photo_id, pos)` then finds the row at pos."""
    return PhotoDropTarget(widget, on_drop, allowed)
