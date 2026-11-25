# OkeyDocu - tests/test_steady_text.py
# Texts of a table column begin on one line, whether they fit their cell or not.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtWidgets import QStyleOptionViewItem, QTableWidgetItem

from okeydocu.ui.common import make_table
from okeydocu.ui.steady_text import SteadyText

SHORT = "RLO 30 m"
LONG = "RLO 100 m   RLO-Offset 0,00   and a good deal more than the column has room for"
TEXTS = (SHORT, LONG, LONG[:-3], LONG[:-9], SHORT + " x", LONG + " and more")


def starts(qtbot) -> set[int]:
    """Where the text of each row begins, in pixels from the left of its cell."""
    table = make_table(["Readings"])
    qtbot.addWidget(table)
    table.horizontalHeader().setSectionResizeMode(table.horizontalHeader().ResizeMode.Fixed)
    table.setRowCount(len(TEXTS))
    for row, text in enumerate(TEXTS):
        table.setItem(row, 0, QTableWidgetItem(text))
    table.setColumnWidth(0, 260)
    table.resize(420, 300)
    table.show()
    qtbot.wait(50)
    image = table.viewport().grab().toImage()
    found = set()
    for row in range(len(TEXTS)):
        rect = table.visualItemRect(table.item(row, 0))
        rows = range(rect.top() + 4, rect.bottom() - 3)
        found.add(next(x for x in range(rect.left(), rect.left() + 60)
                       if any(image.pixelColor(x, y).lightness() < 120 for y in rows)))
    return found


def test_long_and_short_texts_begin_at_the_same_place(qtbot):
    assert len(starts(qtbot)) == 1


def test_a_table_is_made_with_the_steady_delegate(qtbot):
    table = make_table(["Readings"])
    qtbot.addWidget(table)
    assert isinstance(table.itemDelegate(), SteadyText)



def test_a_column_sized_to_its_texts_shows_them_whole(qtbot):
    table = make_table(["T"])
    qtbot.addWidget(table)
    table.setRowCount(1)
    table.setItem(0, 0, QTableWidgetItem("09:00:00"))
    table.resize(420, 300)
    table.show()
    qtbot.wait(50)
    option = QStyleOptionViewItem()
    table.initViewItemOption(option)
    option.rect = table.visualItemRect(table.item(0, 0))
    table.itemDelegate().initStyleOption(option, table.model().index(0, 0))
    assert option.text == "09:00:00"
