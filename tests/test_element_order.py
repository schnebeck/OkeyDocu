# OkeyDocu - tests/test_element_order.py
# Elements side by side keep the order the tester gives them, in the data and in the tree.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtWidgets import QAbstractItemView


Position = QAbstractItemView.DropIndicatorPosition


@pytest.fixture
def press(app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    names = ("Zuleitung", "Antrieb", "Beleuchtung")
    parts = {name: app.db.add_asset(customer, "measuring_point", name, parent_id=press)
             for name in names}
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    return {"press": press, "cabinet": cabinet, **parts}


def names(app, asset_id) -> list[str]:
    return [app.db.asset(i)["name"] for i in app.service.siblings(asset_id)]


def test_a_new_element_goes_behind_its_last_sibling(app, press):
    assert names(app, press["Zuleitung"]) == ["Zuleitung", "Antrieb", "Beleuchtung", "Schrank"]
    below = [row["name"] for row in app.db.assets() if row["parent_id"] == press["press"]]
    assert below == ["Zuleitung", "Antrieb", "Beleuchtung", "Schrank"]


def test_shifting_moves_one_place_and_stops_at_either_end(app, press):
    app.service.shift_element(press["Antrieb"], -1)
    assert names(app, press["Antrieb"]) == ["Antrieb", "Zuleitung", "Beleuchtung", "Schrank"]
    app.service.shift_element(press["Antrieb"], -1)
    assert names(app, press["Antrieb"])[0] == "Antrieb"
    app.service.shift_element(press["cabinet"], 1)
    assert names(app, press["Antrieb"])[-1] == "Schrank"


def test_placing_puts_an_element_beside_another_also_below_another_parent(app, press):
    app.service.place_element(press["cabinet"], press["Zuleitung"], after=True)
    assert names(app, press["Zuleitung"]) == ["Zuleitung", "Schrank", "Antrieb", "Beleuchtung"]
    app.service.move_element(press["Beleuchtung"], press["cabinet"])
    app.service.place_element(press["Antrieb"], press["Beleuchtung"], after=False)
    assert names(app, press["Beleuchtung"]) == ["Antrieb", "Beleuchtung"]
    assert app.db.asset(press["Antrieb"])["parent_id"] == press["cabinet"]


def test_moving_below_another_element_goes_behind_its_children(app, press):
    app.service.move_element(press["Zuleitung"], press["cabinet"])
    app.service.move_element(press["Antrieb"], press["cabinet"])
    assert names(app, press["Zuleitung"]) == ["Zuleitung", "Antrieb"]


def test_a_group_takes_the_place_of_its_first_element(app, press):
    group = app.service.group_elements([press["Antrieb"], press["Beleuchtung"]], "machine",
                                       "Baugruppe")
    assert names(app, group) == ["Zuleitung", "Baugruppe", "Schrank"]
    assert names(app, press["Antrieb"]) == ["Antrieb", "Beleuchtung"]


def test_the_tree_follows_the_order_and_ctrl_up_moves_the_chosen_element(window, app, press):
    page = window.campaign
    campaign = app.service.create(press["press"], "Prüfung", "Prüfer")
    page.refresh()
    page.show_campaign(campaign)
    tree = page.structure
    menu = page.structure_panel.actions
    top = tree.items[press["press"]]
    assert [top.child(i).text(0) for i in range(top.childCount())][:2] == ["Zuleitung", "Antrieb"]
    tree.select(press["Antrieb"])
    menu.shift(-1)
    top = tree.items[press["press"]]
    assert [top.child(i).text(0) for i in range(top.childCount())][:2] == ["Antrieb", "Zuleitung"]
    tree.select(press["press"])
    menu.shift(1)
    assert names(app, press["Antrieb"])[0] == "Antrieb"


@pytest.mark.parametrize(("where", "expected"), [
    (Position.AboveItem, ["Schrank", "Zuleitung", "Antrieb", "Beleuchtung"]),
    (Position.BelowItem, ["Zuleitung", "Schrank", "Antrieb", "Beleuchtung"]),
])
def test_dropping_on_the_line_beside_an_element_reorders(window, app, press, monkeypatch,
                                                         where, expected):
    page = window.campaign
    page.refresh()
    page.show_campaign(app.service.create(press["press"], "Prüfung", "Prüfer"))
    tree = page.structure
    monkeypatch.setattr(tree, "dropIndicatorPosition", lambda: where)
    after = tree._beside(press["Zuleitung"])
    tree._place([press["cabinet"]], press["Zuleitung"], after)
    assert names(app, press["Zuleitung"]) == expected
    monkeypatch.setattr(tree, "dropIndicatorPosition", lambda: Position.OnItem)
    assert tree._beside(press["Zuleitung"]) is None
    assert tree._beside(press["press"]) is None
