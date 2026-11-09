# EasyMeasurement - easymeasurement/ui/view_memory.py
# Remembers how the windows were arranged, so the next start looks the same.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QSplitter, QWidget

from .report_signing import settings
from .side_panel import Section


class ViewMemory:
    """Only what the operator did is kept, and at the moment it is done.

    A splitter is stored when its handle is dragged, not on closing: by then one
    side may be hidden, because no campaign is measuring, and it would come back
    with no room at all.
    """

    def __init__(self):
        self.stored = settings()

    def keep_splitters(self, root: QWidget) -> None:
        """Splitters without a name stay out: their place in the list is no lasting key."""
        for splitter in root.findChildren(QSplitter):
            if splitter.objectName():
                self._keep_splitter(splitter)

    def _keep_splitter(self, splitter: QSplitter) -> None:
        key = f"splitter/{splitter.objectName()}"
        state = self.stored.value(key)
        if isinstance(state, QByteArray):
            # The stored state carries the handle's width too; the program decides that one.
            width, collapsible = splitter.handleWidth(), splitter.childrenCollapsible()
            splitter.restoreState(state)
            splitter.setHandleWidth(width)
            splitter.setChildrenCollapsible(collapsible)
        splitter.splitterMoved.connect(lambda *_: self.stored.setValue(key, splitter.saveState()))

    def keep_section(self, section: Section) -> None:
        key = f"folded/{section.title}"
        section.toggle.setChecked(not self.stored.value(key, False, type=bool))
        section.folded.connect(lambda: self.stored.setValue(key, not section.expanded))

    def keep_toggle(self, key: str, action: QAction, default: bool = True) -> None:
        action.setChecked(self.stored.value(f"view/{key}", default, type=bool))
        action.toggled.connect(lambda checked: self.stored.setValue(f"view/{key}", checked))

    def restore_window(self, key: str, window: QWidget) -> None:
        geometry = self.stored.value(f"window/{key}")
        if isinstance(geometry, QByteArray):
            window.restoreGeometry(geometry)

    def store_window(self, key: str, window: QWidget) -> None:
        self.stored.setValue(f"window/{key}", window.saveGeometry())
