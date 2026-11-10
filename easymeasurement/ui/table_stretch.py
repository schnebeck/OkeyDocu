# EasyMeasurement - easymeasurement/ui/table_stretch.py
# One column of a table takes the room the others leave, but never less than its title.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Qt's own stretching only knows one minimum for all columns of a header. Here the column
is sized by hand whenever the table or another column changes size, so the other columns
keep the width of their contents and a narrow table scrolls sideways instead of cutting
the title."""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QHeaderView, QStyle, QTableView


def title_width(header: QHeaderView, column: int) -> int:
    margins = 2 * header.style().pixelMetric(QStyle.PixelMetric.PM_HeaderMargin)
    title = str(header.model().headerData(column, header.orientation()) or "")
    return header.fontMetrics().horizontalAdvance(title) + margins


class TitledStretch(QObject):
    def __init__(self, table: QTableView, column: int):
        super().__init__(table)
        self.table, self.column = table, column
        header = table.horizontalHeader()
        header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
        header.sectionResized.connect(self._resized)
        table.viewport().installEventFilter(self)
        self.fit()

    def eventFilter(self, watched, event) -> bool:
        if event.type() == QEvent.Type.Resize:
            self.fit()
        return False

    def _resized(self, section: int, _old: int, _new: int) -> None:
        if section != self.column:
            self.fit()

    def fit(self) -> None:
        header = self.table.horizontalHeader()
        others = sum(header.sectionSize(section) for section in range(header.count())
                     if section != self.column and not header.isSectionHidden(section))
        room = self.table.viewport().width() - others
        width = max(title_width(header, self.column), room)
        if header.sectionSize(self.column) != width:
            header.resizeSection(self.column, width)
