# EasyMeasurement - tests/test_structure_ui.py
# The structure beside the table, its menu, the kinds settings and what is due on the start screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.ui.campaign_dialog import CampaignDialog
from easymeasurement.ui.kind_removal import RemoveKindOverlay
from easymeasurement.ui.structure_cleanup import CleanupOverlay
from easymeasurement.ui.structure_tree import UNPLACED


@pytest.fixture
def shown(window, app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    campaign = app.service.create(press, "Prüfung", "Prüfer")
    value = ResultValue("riso", "RISO", Quantity.parse("2MΩ"), Verdict.PASSED, ">1MΩ", "")
    for _ in range(2):
        app.service.add_measurement(campaign, "riso", [value], datetime(2026, 5, 4, 9),
                                    Verdict.PASSED, asset_id=cabinet)
    app.service.add_measurement(campaign, "riso", [value], datetime(2026, 5, 4, 9), Verdict.PASSED)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return {"page": page, "press": press, "cabinet": cabinet, "campaign": campaign,
            "customer": customer}


def test_the_tree_shows_kinds_counts_and_what_has_no_place(shown):
    tree = shown["page"].structure
    cabinet = tree.items[shown["cabinet"]]
    assert cabinet.text(1) == "2" and not cabinet.icon(0).isNull()
    tree.select(UNPLACED)
    assert shown["page"].values.table.rowCount() == 1


def test_measurements_are_booked_by_dropping_them_on_an_element(shown, app):
    page = shown["page"]
    page.structure.select(UNPLACED)
    page.values.table.selectRow(0)
    loose = page.values.table.item(0, 0).data(0x0100)
    app.service.move_measurements([loose], shown["cabinet"])
    page._data_changed()
    assert page.structure.items[shown["cabinet"]].text(1) == "3"


def test_a_new_element_is_named_by_its_kind_and_opened_for_typing(shown, app):
    page = shown["page"]
    page.structure.select(shown["cabinet"])
    page.structure_panel.actions.new_element("cable")
    created = page.structure.current_id()
    assert app.db.asset(created)["parent_id"] == shown["cabinet"]
    assert app.db.asset(created)["name"] == "Leitung"


def test_renaming_in_the_tree_renames_the_element(shown, app, qtbot):
    tree = shown["page"].structure
    item = tree.items[shown["cabinet"]]
    item.setText(0, "Schaltschrank X1")
    qtbot.waitUntil(lambda: app.db.asset(shown["cabinet"])["name"] == "Schaltschrank X1")


def test_new_readings_land_on_the_chosen_element(shown):
    page = shown["page"]
    page.structure.select(shown["cabinet"])
    assert page.place_target(shown["campaign"]) == shown["cabinet"]
    page.structure.select(shown["press"])
    assert page.place_target(shown["campaign"]) == shown["press"]


def test_the_side_panel_names_the_chosen_element(shown, app):
    app.db.set_asset_features(shown["cabinet"], {"ip_rating": "IP54"})
    page = shown["page"]
    page.structure.select(shown["cabinet"])
    assert page.place.kind.text() == "Verteiler"
    assert "IP54" in page.place.details.text() and "Material" not in page.place.details.text()


def test_cleanup_lists_only_empty_branches(shown, app):
    spare = app.service.add_element(shown["press"], "measuring_point", "Leer")
    overlay = CleanupOverlay(app, shown["press"], app.service.empty_elements(shown["press"]))
    assert overlay.chosen() == [spare]
    assert overlay.ok_button.text() == "1 entfernen"


def test_grouping_machines_under_an_installation(window, app):
    customer = app.db.add_customer("Werk")
    first = app.db.add_asset(customer, "machine", "Säge")
    second = app.db.add_asset(customer, "machine", "Fräse")
    page = window.master_data
    page.refresh()
    page.select_customer(customer)
    tree = page.tree
    tree.items[first].setSelected(True)
    tree.items[second].setSelected(True)
    page.structure.actions.group("installation")
    group = app.db.asset(first)["parent_id"]
    assert app.db.asset(group)["kind"] == "installation"
    assert app.db.asset(second)["parent_id"] == group


def test_a_used_kind_is_removed_with_a_replacement(window, app, shown, monkeypatch):
    kinds = window.kinds
    kinds.refresh(select="distribution_board")
    monkeypatch.setattr(RemoveKindOverlay, "exec", lambda overlay: 1)
    kinds._remove()
    assert app.db.kind("distribution_board") is None
    assert app.db.asset(shown["cabinet"])["kind"] == "measuring_point"


def test_a_new_kind_gets_features(window, app):
    kinds = window.kinds
    kinds._add()
    key = kinds.current_key()
    kinds.features.add()
    kinds.features.table.item(0, 0).setText("Leistung")
    kinds.features.table.item(0, 1).setText("kW")
    feature, = app.db.kind(key).features
    assert (feature.label, feature.unit) == ("Leistung", "kW")


def test_a_follow_up_is_started_from_the_start_screen(window, app, monkeypatch):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    first = app.service.create(press, "Prüfung", "Prüfer")
    value = ResultValue("riso", "RISO", Quantity.parse("0.2MΩ"), Verdict.FAILED, ">1MΩ", "")
    app.service.add_measurement(first, "riso", [value], datetime(2026, 5, 4), Verdict.FAILED)
    app.service.close(first)
    app.db.add_user("A. Prüfer")
    page = window.campaign
    page.refresh()
    page.show_home()
    row = page.home.due.rows.itemAt(0).widget()
    seen = []

    def accept(dialog):
        seen.append((dialog.asset.currentData(), dialog.title.text()))
        return 1

    monkeypatch.setattr(CampaignDialog, "exec", accept)
    row.button.click()
    assert seen == [(press, "Nachprüfung: Prüfung")]
    assert app.service.open_follow_ups() == []


def test_searching_the_structure_keeps_the_way_to_a_hit(shown):
    panel = shown["page"].structure_panel
    panel.search.setText("schrank")
    tree = panel.tree
    assert not tree.items[shown["cabinet"]].isHidden()
    assert not tree.items[shown["press"]].isHidden()  # the way to it
    panel.search.setText("nirgends")
    assert tree.items[shown["press"]].isHidden()


def test_features_reach_the_report(app, shown):
    from easymeasurement.reporting.context import _features
    app.db.set_asset_features(shown["press"], {"rated_current": "16", "year_of_manufacture": ""})
    assert _features(app.db, app.db.asset(shown["press"])) == [("Nennstrom", "16\u202fA")]
