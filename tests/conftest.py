# EasyMeasurement - tests/conftest.py
# Shared fixtures. All instrument data here is synthetic.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
from pathlib import Path

import pytest

# The default offscreen screen measures 800 x 800, smaller than any real one.
SCREEN = Path(__file__).with_name("offscreen_screen.json")
os.environ.setdefault("QT_QPA_PLATFORM", f"offscreen:configfile={SCREEN}")

from PySide6.QtWidgets import QMessageBox

from easymeasurement.__main__ import build_context
from easymeasurement.campaign.plan import load_plans
from easymeasurement.campaign.seal import KWalletKeyStore
from easymeasurement.campaign.service import CampaignService
from easymeasurement.l10n import set_language
from easymeasurement.store import Database
from easymeasurement.ui.main_window import MainWindow

set_language("de")  # the German texts are what the tests read


@pytest.fixture(autouse=True)
def isolated_data(tmp_path, monkeypatch):
    monkeypatch.setenv("EASYMEASUREMENT_DATA", str(tmp_path / "data"))


@pytest.fixture(autouse=True)
def no_real_instruments(monkeypatch):
    """Tests must not depend on what happens to be paired with this computer."""
    monkeypatch.setattr("easymeasurement.ui.campaign_dialog.find_instruments", lambda: [])
    monkeypatch.setattr("easymeasurement.ui.settings_dialog.find_instruments", lambda: [])


@pytest.fixture(autouse=True)
def no_real_wallet(monkeypatch):
    """Tests must never touch the wallet of the person running them."""
    monkeypatch.setattr(KWalletKeyStore, "key", lambda self: b"test" * 8)


@pytest.fixture(autouse=True)
def no_open_questions(monkeypatch):
    """A modal question would hang a test. Whoever expects one answers it himself."""
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.No)
    monkeypatch.setattr("easymeasurement.ui.instrument_control.ask_clock_sync",
                        lambda *_: False)  # set by hand, unless a test says otherwise


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "test.sqlite")
    yield database
    database.close()


@pytest.fixture
def service(db, tmp_path):
    return CampaignService(db, tmp_path / "archive")


@pytest.fixture
def plan():
    return load_plans()[0]


@pytest.fixture
def asset_id(db):
    customer = db.add_customer("Musterbau GmbH", city="Musterstadt")
    return db.add_asset(customer, "machine", "Presse 7", identifier="M-007")


@pytest.fixture
def app():
    context = build_context()
    yield context
    context.db.close()


@pytest.fixture
def window(qtbot, app):
    main = MainWindow(app)
    qtbot.addWidget(main)
    main.show()
    yield main
    main.campaign.shut_down()


@pytest.fixture
def asset(app):
    return app.db.add_asset(app.db.add_customer("Muster AG"), "installation", "Halle")
