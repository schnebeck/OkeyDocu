# OkeyDocu - okeydocu/ui/place_line.py
# Where a measurement is booked: the element by name, the way to it small above.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..campaign.service import LOCATION_SEPARATOR
from ..l10n import tr
from .common import AppContext
from .kind_catalog import KindCatalog

WAY = "  ›  "


class _WayLabel(QLabel):
    """Shortened from the left: the parts next to the element say the most about it."""

    def __init__(self):
        super().__init__()
        self.full = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        self.setEnabled(False)
        font = self.font()
        font.setPointSizeF(font.pointSizeF() * 0.9)
        self.setFont(font)

    def show_way(self, text: str) -> None:
        self.full = text
        self.setToolTip(text)
        self._elide()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._elide()

    def _elide(self) -> None:
        self.setText(self.fontMetrics().elidedText(
            self.full, Qt.TextElideMode.ElideLeft, max(self.width(), 1)))


class PlaceLine(QWidget):
    """The element and its kind's icon; the pencil books the measurement elsewhere."""

    move_requested = Signal()
    chosen = Signal(int)  # the name was clicked: show this element

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.asset_id: int | None = None
        self.icon = QLabel()
        self.way = _WayLabel()
        self.name = QLabel()
        self.name.setTextFormat(Qt.TextFormat.RichText)
        self.name.setToolTip(tr("Show in the structure tree"))
        self.name.linkActivated.connect(lambda _: self.chosen.emit(self.asset_id))
        self.button = QToolButton()
        fallback = self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        self.button.setIcon(QIcon.fromTheme("document-edit", fallback))
        self.button.setAutoRaise(True)
        self.button.setToolTip(tr("Assign to another element …"))
        self.button.setAccessibleName(tr("Change measuring location"))
        self.button.clicked.connect(self.move_requested)
        names = QVBoxLayout()
        names.setSpacing(0)
        names.addWidget(self.way)
        names.addWidget(self.name)
        # Two lines that must not be pressed into one when the side panel runs short.
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.icon)
        row.addLayout(names, 1)
        row.addWidget(self.button, 0, Qt.AlignmentFlag.AlignVCenter)

    def show_asset(self, asset_id: int, movable: bool) -> None:
        self.asset_id = asset_id
        asset = self.app.db.asset(asset_id)
        self.icon.setPixmap(KindCatalog(self.app.db).icon(asset["kind"]).pixmap(20, 20))
        parts = self.app.service.place_path(asset_id).split(LOCATION_SEPARATOR)
        self.way.show_way(WAY.join(parts[:-1]))
        self.way.setVisible(len(parts) > 1)
        self.name.setText(f'<a href="element" style="text-decoration:none">'
                          f'{escape(parts[-1])}</a>')
        self.button.setVisible(movable)
