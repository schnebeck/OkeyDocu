# OkeyDocu - tests/test_campaign_delete.py
# Deleting an open campaign: asked first, gone completely, and nothing of it left for the next one.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import sqlite3
from datetime import datetime

import pytest

from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.campaign.seal import SealState
from okeydocu.store import CampaignClosed
from okeydocu.ui.campaign_delete import loss_text

from .workspace_helpers import start, with_asset


def _measure(app, campaign):
    value = ResultValue("riso", "RISO", Quantity.parse("2MΩ"), Verdict.PASSED, ">1MΩ", "")
    return app.service.add_measurement(campaign, "riso", [value], datetime(2026, 5, 4, 9),
                                       Verdict.PASSED)


@pytest.fixture
def campaign(app, asset):
    return app.service.create(asset, "Prüfung", "Prüfer")


# The rule --------------------------------------------------------------------


def test_an_open_campaign_goes_with_everything_in_it(app, campaign):
    _measure(app, campaign)
    app.service.add_comment(campaign, "Notiz")
    folder = app.service.folder(campaign)
    assert app.service.delete_campaign(campaign) == folder
    assert app.service.campaign(campaign) is None
    for table in ("measurements", "attachments", "steps"):
        assert app.db.query(f"SELECT * FROM {table} WHERE campaign_id=?", campaign) == []
    assert app.db.query("SELECT * FROM measured_values") == []


def _sealed_pair(app, asset):
    """Two closed campaigns: the second one's seal points at the first."""
    first = app.service.create(asset, "Erste", "Prüfer")
    app.service.close(first)
    second = app.service.create(asset, "Zweite", "Prüfer")
    app.service.close(second)
    return first, second


def test_a_sealed_campaign_goes_with_its_reports(app, asset):
    from okeydocu.reporting.template import default_template_text
    first, second = _sealed_pair(app, asset)
    app.archive.generate(first, "Standard", default_template_text(), "de")
    app.service.delete_campaign(first)
    assert app.service.campaign(first) is None
    assert app.archive.reports(first) == []
    note, = app.db.query("SELECT * FROM deleted_campaigns")
    assert note["title"] == "Erste" and note["seal_mac"]


def test_the_seal_chain_holds_after_an_open_deletion(app, asset):
    first, second = _sealed_pair(app, asset)
    app.service.delete_campaign(first)
    assert app.service.check_seal(second).state is SealState.INTACT


def test_deleting_behind_the_programs_back_still_breaks_the_chain(app, asset):
    first, second = _sealed_pair(app, asset)
    with pytest.raises(CampaignClosed):
        app.db.execute("DELETE FROM campaigns WHERE id=?", first)
    app.db.connection.execute("DROP TRIGGER campaign_no_delete")
    app.db.execute("DELETE FROM campaigns WHERE id=?", first)
    check = app.service.check_seal(second, thorough=False)
    assert "Eine früher versiegelte Kampagne fehlt." in check.reasons


def test_a_forged_deletion_note_is_found(app, asset):
    first, second = _sealed_pair(app, asset)
    seal = app.service.campaign(first)["seal"]
    app.db.connection.execute("DROP TRIGGER campaign_no_delete")
    app.db.execute("INSERT INTO deleted_campaigns (uuid, title, seal, seal_mac, deleted_at)"
                   " VALUES ('x', 'Erste', ?, 'falsch', '2026-01-01T00:00:00')", seal)
    app.db.execute("DELETE FROM campaigns WHERE id=?", first)
    check = app.service.check_seal(second)
    assert "Der Löschvermerk einer früheren Kampagne ist nicht echt." in check.reasons


def test_deletion_notes_are_kept(app, asset):
    first, _ = _sealed_pair(app, asset)
    app.service.delete_campaign(first)
    with pytest.raises(sqlite3.IntegrityError):
        app.db.execute("DELETE FROM deleted_campaigns")


def test_a_reading_on_a_reused_id_does_not_inherit_changes(app, asset, campaign):
    measurement = _measure(app, campaign)
    app.service.edit_measurement(measurement, {"verdict": "failed"})
    app.service.delete_campaign(campaign)
    again = app.service.create(asset, "Neu", "Prüfer")
    reused = _measure(app, again)
    assert reused == measurement  # SQLite gives the highest free ID out again
    assert app.service.measurement_changes(reused) == []


def test_the_question_names_what_is_lost(app, campaign):
    record = app.service.campaign(campaign)
    assert loss_text(app, record) == "Die Kampagne enthält noch nichts."
    _measure(app, campaign)
    assert loss_text(app, record) == "1 Messung geht mit verloren."
    app.service.add_comment(campaign, "Notiz")
    assert loss_text(app, record) == "1 Messung und 1 Notiz oder Datei gehen mit verloren."


# The screen ------------------------------------------------------------------


def _shown(window, app, campaign):
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    return window.campaign


def test_saying_no_keeps_the_campaign(window, app, campaign, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.ask_delete", lambda *_: False)
    _measure(app, campaign)
    page = _shown(window, app, campaign)
    page.delete_action.trigger()
    assert app.service.campaign(campaign) is not None
    assert page.campaign_id == campaign


def test_deleting_returns_to_the_overview(window, app, campaign, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.ask_delete", lambda *_: True)
    trashed = []
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.dispose",
                        lambda folder: trashed.append(folder) or True)
    page = _shown(window, app, campaign)
    page.delete_action.trigger()
    assert app.service.campaign(campaign) is None
    assert campaign not in page.list.items
    assert page.pages.currentWidget() is page.home
    assert page.home.cards == []
    assert len(trashed) == 1
    assert page.notice.text() == "„Prüfung“ gelöscht."


def test_files_that_stay_are_named(window, app, campaign, monkeypatch):
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.ask_delete", lambda *_: True)
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.dispose", lambda _: False)
    page = _shown(window, app, campaign)
    page.delete_action.trigger()
    assert "Ihre Dateien liegen noch in" in page.notice.text()


def test_deleting_the_campaign_measuring_disconnects_first(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    page = window.campaign
    live = page.live_id
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.ask_delete", lambda *_: True)
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.dispose", lambda _: True)
    page.delete_action.trigger()
    assert page.session is None and page.live_id is None
    assert app.service.campaign(live) is None


def test_a_closed_campaign_can_be_deleted_too(window, app, campaign, monkeypatch):
    app.service.close(campaign)
    page = _shown(window, app, campaign)
    assert page.menu_actions()[-1] is page.delete_action
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.ask_delete", lambda *_: True)
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.dispose", lambda _: True)
    page.delete_action.trigger()
    assert app.service.campaign(campaign) is None


def test_the_context_menu_ends_with_deleting(window, app, campaign):
    page = _shown(window, app, campaign)
    assert page.menu_actions()[-1] is page.delete_action


def test_an_empty_campaign_goes_without_asking_and_offers_no_confirming(window, app, asset,
                                                                          monkeypatch):
    asked = []
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.ask_delete",
                        lambda *_: asked.append(True) or False)
    empty = app.service.create(asset, "Leer", "Prüfer")
    page = _shown(window, app, empty)
    assert page.header.delete_button.isVisibleTo(page)
    assert not page.header.finish_button.isVisibleTo(page)
    assert not page.finish_action.isEnabled()
    page.header.delete_button.click()
    assert app.service.campaign(empty) is None and asked == []


def test_a_card_on_the_overview_offers_the_campaigns_menu(window, app, campaign, monkeypatch):
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QContextMenuEvent

    page = _shown(window, app, campaign)
    page.show_home()
    asked = []
    monkeypatch.setattr(page, "_campaign_menu", lambda chosen, where: asked.append(chosen))
    card = page.home.cards[0]
    card.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, QPoint(5, 5)))
    assert asked == [campaign]
