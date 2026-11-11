# EasyMeasurement - tests/test_table_columns.py
# Columns of the measurement table: shown or hidden by hand, sorted and moved, kept for later.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.ui.table_columns import TableColumns

PLACE, FUNCTION, VALUES = 4, 5, 6


@pytest.fixture
def page(window, app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    for day, text in ((datetime(2025, 12, 10, 9), "10MΩ"), (datetime(2026, 1, 2, 9), "2MΩ"),
                      (datetime(2025, 12, 31, 9), "300kΩ")):
        value = ResultValue("riso", "RISO", Quantity.parse(text), Verdict.PASSED, ">1MΩ", "")
        app.service.add_measurement(campaign, "riso", [value], day, Verdict.PASSED,
                                    location="Presse / Schrank")
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return page.values


def _column(values, column):
    return [values.table.item(row, column).text() for row in range(values.table.rowCount())]


def _menu(values, clicked=-1) -> dict:
    menu = values.columns.fill(QMenu(values), clicked)
    return {action.text(): action for action in menu.actions() if action.text()}


def test_dates_sort_by_time_not_by_their_text(page):
    assert [text[:10] for text in _column(page, 0)] == ["10.12.2025", "31.12.2025", "02.01.2026"]


def test_values_sort_by_size_not_by_their_text(page):
    _menu(page, VALUES)["Nach „Messwerte“ aufsteigend sortieren"].trigger()
    assert [text.split(" ", 1)[1] for text in _column(page, VALUES)] == ["300\u202fkΩ", "2\u202fMΩ", "10\u202fMΩ"]
    descending = _menu(page, VALUES)["Nach „Messwerte“ absteigend sortieren"]
    assert not descending.isChecked()
    descending.trigger()
    assert [text.split(" ", 1)[1] for text in _column(page, VALUES)] == ["10\u202fMΩ", "2\u202fMΩ", "300\u202fkΩ"]


def test_the_newest_reading_is_chosen_wherever_the_sorting_put_it(page):
    page.table.horizontalHeader().setSortIndicator(0, Qt.SortOrder.DescendingOrder)
    page.show_newest()
    assert page.table.currentItem().row() == 1  # the 31st was entered last


def test_a_column_switched_off_stays_off(page):
    assert page.table.isColumnHidden(PLACE)  # the same in every row, so it is said above
    assert "Messort" in page.common.text()
    _menu(page)["Messort"].setChecked(False)
    assert page.table.isColumnHidden(PLACE) and "Messort" not in page.common.text()
    _menu(page)["Gleiche Werte über der Tabelle nennen"].setChecked(False)
    assert page.table.isColumnHidden(PLACE) and not page.table.isColumnHidden(FUNCTION)


def test_shared_values_may_stay_in_their_columns(page):
    _menu(page)["Gleiche Werte über der Tabelle nennen"].setChecked(False)
    assert not page.table.isColumnHidden(PLACE)
    assert "Messort" not in page.common.text()


def test_the_last_column_cannot_be_switched_off(page):
    keep = ("Messwerte", "Gleiche Werte über der Tabelle nennen")
    for text, action in _menu(page).items():
        if action.isCheckable() and text not in keep:
            action.setChecked(False)
    assert not _menu(page)["Messwerte"].isEnabled()


def test_order_sorting_and_choice_are_kept_for_the_next_start(page):
    header = page.table.horizontalHeader()
    header.moveSection(header.visualIndex(VALUES), 0)
    header.setSortIndicator(VALUES, Qt.SortOrder.DescendingOrder)
    _menu(page)["Erfassung"].setChecked(False)
    later = TableColumns(page.table.__class__(1, page.table.columnCount()), "CampaignValues")
    again = later.table.horizontalHeader()
    assert again.logicalIndex(0) == VALUES
    assert (again.sortIndicatorSection(), again.sortIndicatorOrder()) == (
        VALUES, Qt.SortOrder.DescendingOrder)
    assert 9 in later.off


def test_reset_brings_everything_back(page):
    header = page.table.horizontalHeader()
    header.moveSection(header.visualIndex(VALUES), 0)
    _menu(page)["Fotos"].setChecked(False)
    page.columns.reset()
    assert header.logicalIndex(0) == 0 and page.columns.off == set()
    assert header.sortIndicatorSection() == 0
