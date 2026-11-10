# EasyMeasurement - tests/test_workspace_start.py
# The start screen, starting a campaign, and importing data from the menu.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QFileDialog

from easymeasurement.importing.izytron import ImportFailed
from easymeasurement.ui.measurement_overlays import ImportOverlay
from easymeasurement.ui.status_badges import GOOD

from .workspace_helpers import plan_title, start, with_asset


# First impression ------------------------------------------------------------


def test_the_app_opens_on_the_campaign_workspace(window):
    assert window.centralWidget() is window.campaign
    assert window.campaign.pages.currentWidget() is window.campaign.home


def test_without_an_asset_the_way_to_master_data_is_shown(window):
    home = window.campaign.home
    assert not home.start_button.isEnabled()
    assert home.no_asset.isVisible()
    home.master_data_button.click()
    assert window.master_data.isVisible()
    assert window.campaign.isVisible()


def test_creating_an_asset_enables_the_start(window, app):
    with_asset(window, app)
    assert window.campaign.home.start_button.isEnabled()
    assert not window.campaign.home.no_asset.isVisible()


def test_an_empty_list_shows_no_groups(window, app):
    with_asset(window, app)
    assert window.campaign.list.running.isHidden()
    assert window.campaign.list.closed.isHidden()


# After starting --------------------------------------------------------------


def test_starting_leads_away_from_the_start_screen(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    assert window.campaign.pages.currentWidget() is window.campaign.running


def test_the_running_campaign_is_named_on_screen(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    header = window.campaign.header
    assert header.title.text() == "Prüfung Halle"
    assert "Halle 1" in header.details.text()
    assert "A. Prüfer" in header.details.text()


def test_a_new_campaign_stays_reachable_during_the_work(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    assert not window.campaign.home.start_button.isVisible()
    assert window.campaign.new_action.isEnabled()
    window.campaign.drawer.react(QPoint(2, 200))  # the mouse at the left window edge
    assert window.campaign.list.new_button.isVisible()


def test_manual_campaign_says_what_to_do_and_shows_no_connection(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    free = window.campaign.free
    assert "von Hand" in free.guidance.text()
    assert window.campaign.values.manual_button.isVisible()
    assert not window.campaign.link.isVisible()


def test_plan_campaign_shows_the_steps(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, plan_title(window), simulated=True)
    campaign = window.campaign
    assert campaign.current_work() is window.guided
    assert window.guided.steps.count() > 0
    assert campaign.plan_section.isVisible()
    assert campaign.link.kind == GOOD


def test_imported_campaign_opens_without_an_instrument(window, app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Import", "P", None, "izytron")
    window.campaign.enter(campaign)
    free = window.campaign.free
    assert "Importierte Daten" in free.guidance.text()
    assert window.campaign.session is None
    assert window.campaign.current_work() is free
    assert window.campaign.campaign_id == campaign


def test_import_from_the_menu_leaves_the_original_alone(window, app, monkeypatch, tmp_path):
    original = tmp_path / "izytron.sqlite"
    original.write_bytes(b"kein SQLite")
    seen = []

    def fake_import(service, path, offset):
        seen.append((path, offset))
        raise ImportFailed("Die Datenbank enthält keine Prüfungen.")

    errors = []
    monkeypatch.setattr("easymeasurement.ui.main_window.import_day", fake_import)
    monkeypatch.setattr("easymeasurement.ui.main_window.show_error", lambda _, t: errors.append(t))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(original), ""))
    monkeypatch.setattr(ImportOverlay, "exec", lambda self: self.offset.setValue(-600) or 1)
    window.import_action.trigger()
    assert seen[0][0] != original
    assert seen[0][1] == -600
    assert errors == ["Die Datenbank enthält keine Prüfungen."]


def test_a_file_that_is_no_database_is_explained(window, monkeypatch, tmp_path):
    other = tmp_path / "bild.sqlite"
    other.write_bytes(b"kein SQLite" * 100)
    errors = []
    monkeypatch.setattr("easymeasurement.ui.main_window.show_error", lambda _, t: errors.append(t))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *_: (str(other), ""))
    monkeypatch.setattr(ImportOverlay, "exec", lambda self: 1)
    window.import_action.trigger()
    assert "keine lesbare" in errors[0]
