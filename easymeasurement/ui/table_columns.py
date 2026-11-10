# EasyMeasurement - easymeasurement/ui/table_columns.py
# Which columns a table shows, in which order and sorted by which, kept for the next start.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import QMenu, QTableWidget, QTableWidgetItem

from ..l10n import N_, tr
from .report_signing import settings

SORT_KEY = Qt.ItemDataRole.UserRole + 20
GROUP = Qt.ItemDataRole.UserRole + 21  # lines that stay together, as a run and its steps
ORDER = Qt.ItemDataRole.UserRole + 22  # their order inside the group, the head first
HEAD = Qt.ItemDataRole.UserRole + 23  # what a member sorts by among others: its head's key


def _key(item: QTableWidgetItem):
    for role in (HEAD, SORT_KEY):
        if item.data(role) is not None:
            return item.data(role)
    return item.text().casefold()


class SortItem(QTableWidgetItem):
    """Ordered by a key of its own where the text would sort wrongly, as dates and numbers do.

    Lines of one group keep together under their head, whichever column sorts and in
    which direction: inside the group the order never turns.
    """

    def __init__(self, text: str, key=None):
        super().__init__(text)
        if key is not None:
            self.setData(SORT_KEY, key)

    def __lt__(self, other: QTableWidgetItem) -> bool:
        group = self.data(GROUP)
        if group is not None and group == other.data(GROUP):
            table = self.tableWidget()
            down = (table is not None and table.horizontalHeader().sortIndicatorOrder()
                    == Qt.SortOrder.DescendingOrder)
            mine, theirs = self.data(ORDER), other.data(ORDER)
            return mine > theirs if down else mine < theirs
        mine, theirs = _key(self), _key(other)
        if type(mine) is not type(theirs):
            return str(mine) < str(theirs)
        return mine < theirs


class TableColumns(QObject):
    """Columns are moved by their heading, sorted by a click on it and picked in its menu.

    A column whose value is the same in every row may give way to a line above the table
    (`gather`); a column switched off by hand stays off either way.
    """

    changed = Signal()  # what is shown has to be worked out again

    def __init__(self, table: QTableWidget, name: str, never: tuple[int, ...] = ()):
        super().__init__(table)
        self.table = table
        self.key = f"tables/{name}"
        self.never = set(never)  # said elsewhere on the screen
        header = table.horizontalHeader()
        stored = settings()
        self.off = {int(c) for c in stored.value(f"{self.key}/hidden", "", type=str).split()}
        self.gather = stored.value(f"{self.key}/gather", True, type=bool)
        order = [int(c) for c in stored.value(f"{self.key}/order", "", type=str).split()]
        if sorted(order) == list(range(header.count())):
            for visual, logical in enumerate(order):
                header.moveSection(header.visualIndex(logical), visual)
        header.setSectionsMovable(True)
        header.setFirstSectionMovable(True)
        header.setSortIndicatorShown(True)
        header.setSortIndicator(stored.value(f"{self.key}/sort", 0, type=int),
                                Qt.SortOrder(stored.value(f"{self.key}/order_by", 0, type=int)))
        table.setSortingEnabled(True)
        header.sectionMoved.connect(lambda *_: self._store())
        header.sortIndicatorChanged.connect(lambda *_: self._store())
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.setToolTip(tr("Click sorts, dragging moves, right-click chooses columns"))
        header.customContextMenuRequested.connect(self._context_menu)

    def apply(self, same: set[int]) -> set[int]:
        """Shows and hides every column; returns the ones whose shared value goes on top."""
        gathered = same - self.off - self.never if self.gather else set()
        for column in range(self.table.columnCount()):
            hidden = column in self.never or column in self.off or column in gathered
            self.table.setColumnHidden(column, hidden)
        return gathered

    def fill(self, menu: QMenu, clicked: int = -1) -> QMenu:
        """Sorting by the column under the mouse first, then which columns there are."""
        menu.clear()
        header = self.table.horizontalHeader()
        if clicked >= 0:
            name = self.table.horizontalHeaderItem(clicked).text()
            for text, order in ((N_("Sort by “{name}” ascending"), Qt.SortOrder.AscendingOrder),
                                (N_("Sort by “{name}” descending"), Qt.SortOrder.DescendingOrder)):
                action = menu.addAction(tr(text, name=name))
                action.setCheckable(True)
                action.setChecked(header.sortIndicatorSection() == clicked
                                  and header.sortIndicatorOrder() == order)
                action.triggered.connect(
                    lambda _, order=order: header.setSortIndicator(clicked, order))
        menu.addSection(tr("Columns"))
        offered = [header.logicalIndex(visual) for visual in range(header.count())]
        offered = [column for column in offered if column not in self.never]
        shown = [column for column in offered if column not in self.off]
        for column in offered:
            action = menu.addAction(self.table.horizontalHeaderItem(column).text())
            action.setCheckable(True)
            action.setChecked(column not in self.off)
            # The last column left cannot go, a table without any would be a blank box.
            action.setEnabled(shown != [column])
            action.toggled.connect(lambda on, column=column: self._switch(column, on))
        menu.addSeparator()
        gather = menu.addAction(tr("Name equal values above the table"))
        gather.setCheckable(True)
        gather.setChecked(self.gather)
        gather.toggled.connect(self._gather)
        menu.addAction(tr("Reset columns"), self.reset)
        return menu

    def _context_menu(self, point) -> None:
        header = self.table.horizontalHeader()
        menu = self.fill(QMenu(header), header.logicalIndexAt(point))
        menu.exec(header.mapToGlobal(point))
        menu.deleteLater()

    def reset(self) -> None:
        header = self.table.horizontalHeader()
        for logical in range(header.count()):
            header.moveSection(header.visualIndex(logical), logical)
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.off, self.gather = set(), True
        self._store()
        self.changed.emit()

    def _switch(self, column: int, on: bool) -> None:
        (self.off.discard if on else self.off.add)(column)
        self._store()
        self.changed.emit()

    def _gather(self, on: bool) -> None:
        self.gather = on
        self._store()
        self.changed.emit()

    def _store(self) -> None:
        header = self.table.horizontalHeader()
        stored = settings()
        stored.setValue(f"{self.key}/hidden", " ".join(map(str, sorted(self.off))))
        stored.setValue(f"{self.key}/gather", self.gather)
        stored.setValue(f"{self.key}/order",
                        " ".join(str(header.logicalIndex(v)) for v in range(header.count())))
        stored.setValue(f"{self.key}/sort", header.sortIndicatorSection())
        stored.setValue(f"{self.key}/order_by", header.sortIndicatorOrder().value)
