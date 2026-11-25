# OkeyDocu - tests/test_side_width.py
# l10n: de
# The side panel beside a campaign has room for what it shows, whatever is chosen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from okeydocu.l10n import speaking
from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.ui.main_window import MainWindow

LONG = "Hydraulikpresse mit Vorschubeinrichtung HP-200"


def measure(app, campaign, asset, minute, function="riso"):
    value = ResultValue(function, function.upper(), Quantity.parse("200MΩ"), Verdict.PASSED)
    app.service.add_measurement(campaign, function, [value], datetime(2026, 11, 14, 9, minute),
                                Verdict.PASSED, asset_id=asset)


@pytest.fixture
def follower(app):
    """A campaign that follows an open template: one point taken, one still open."""
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", LONG)
    cabinet = app.db.add_asset(customer, "distribution_board", "Schaltschrank", machine)
    first = app.service.create(machine, "Erstprüfung", "Prüfer")
    measure(app, first, machine, 1)
    measure(app, first, cabinet, 2, "rlo")
    app.service.close(first)
    campaign = app.service.create(machine, "Wiederholung", "Prüfer")
    app.service.use_template(campaign, app.service.template_from(first, "Presse"))
    measure(app, campaign, machine, 5)
    app.service.rematch(campaign)
    return campaign


def shown(qtbot, app, campaign):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.resize(1500, 900)
    window.show()
    window.campaign.show_campaign(campaign)
    qtbot.wait(50)
    return window


@pytest.mark.parametrize("language", ("de", "en"))
def test_the_panel_is_as_wide_as_what_it_shows_needs(qtbot, app, follower, language):
    with speaking(language):
        window = shown(qtbot, app, follower)
        page = window.campaign
        table, side = page.values.table, page.side
        assert table.rowCount() == 2
        for row in range(table.rowCount()):  # a reading, then an open point
            table.selectRow(row)
            qtbot.wait(50)
            assert side.widget().minimumSizeHint().width() <= side.viewport().width(), row
        page.shut_down()


def test_the_panel_keeps_its_width_when_the_choice_changes(qtbot, app, follower):
    window = shown(qtbot, app, follower)
    page = window.campaign
    widths = []
    for row in (0, 1, 0, 1, 0, 1):
        page.values.table.selectRow(row)
        qtbot.wait(50)
        widths.append(page.side.width())
    # Having shown both once, it has the width for either and keeps it.
    assert len(set(widths[2:])) == 1 and widths == sorted(widths)
    page.shut_down()


def test_a_long_element_name_is_cut_and_still_leads_to_its_element(qtbot, app, follower):
    window = shown(qtbot, app, follower)
    page = window.campaign
    page.values.table.selectRow(0)
    qtbot.wait(50)
    name = page.values.editor.place.name
    assert name.text() == LONG and name.is_cut()
    seen = []
    page.values.editor.place.chosen.connect(seen.append)
    QTest.mouseClick(name, Qt.MouseButton.LeftButton, pos=QPoint(5, 5))
    assert len(seen) == 1
    page.shut_down()
