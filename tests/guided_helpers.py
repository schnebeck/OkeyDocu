# EasyMeasurement - tests/guided_helpers.py
# Fixtures and steps of the guided flow in the real window, with the simulator.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from easymeasurement.__main__ import build_context
from easymeasurement.campaign.plan import load_plans
from easymeasurement.ui import common
from easymeasurement.ui.main_window import MainWindow


@pytest.fixture
def window(qtbot, monkeypatch):
    monkeypatch.setattr(common, "SIMULATED_FAILURE_RATE", 0.0)
    app = build_context()
    customer = app.db.add_customer("Musterbau GmbH")
    asset = app.db.add_asset(customer, "machine", "Presse 7")
    main = MainWindow(app)
    main.app = app
    main.asset = asset
    main.resize(1360, 900)
    qtbot.addWidget(main)
    main.show()
    yield main
    app.db.close()


@pytest.fixture
def page(window):
    window.guided.start_campaign(window.asset, load_plans()[0], "Prüfung", "Prüfer", "simulator")
    return window.guided


def shown(page):
    return page.window().campaign.values.table.rowCount()


def click_wire(view, index):
    point = view.mapFromScene(view.wire_point(index))
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(point.x(), point.y()))


def connect_all(page):
    for index in range(page.wiring.total):
        click_wire(page.wiring, index)
    page.device_set.setChecked(True)


def run_step(page, readings=1):
    connect_all(page)
    page.confirm_button.click()
    for _ in range(readings):
        page.simulate_button.click()
    page.next_button.click()
