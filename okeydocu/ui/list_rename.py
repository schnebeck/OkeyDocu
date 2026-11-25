# OkeyDocu - okeydocu/ui/list_rename.py
# From an entry of a list to the field that holds its name.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QListWidget


def rename_from_list(entries: QListWidget, rename: Callable[[], None], tip: str) -> None:
    """A double click on an entry or F2 on the list calls `rename`; `tip` says so."""
    entries.setToolTip(tip)
    entries.itemDoubleClicked.connect(lambda _: rename())
    shortcut = QShortcut(QKeySequence(Qt.Key.Key_F2), entries)
    shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
    shortcut.activated.connect(rename)
