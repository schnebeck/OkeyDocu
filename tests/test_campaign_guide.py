# OkeyDocu - tests/test_campaign_guide.py
# A guided measurement opened from a campaign measuring without a plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The simulator borrows the PROFITEST PRIME's guides and panel, so the whole way runs
without an instrument."""

from dataclasses import replace

import pytest

from okeydocu.devices import registry
from okeydocu.devices.base import SelectorPosition
from okeydocu.devices.guide import MEASURE
from okeydocu.devices.profitest_prime import panel
from okeydocu.devices.profitest_prime.guides import GUIDES, guide_for
from okeydocu.l10n import speaking

from .workspace_helpers import start, with_asset


@pytest.fixture
def page(window, app, monkeypatch):
    simulator = registry.driver_info("simulator")
    monkeypatch.setitem(registry._DRIVERS, "simulator", replace(
        simulator, panel=panel.DRAWING, guide=guide_for, guided=tuple(GUIDES)))
    with_asset(window, app)
    with speaking("de"):
        start(window, monkeypatch, simulated=True)
    return window.campaign


def meter_of(page):
    return page.app.devices.driver(page.app.service.campaign(page.campaign_id))


def test_the_first_measurement_of_a_kind_is_guided_and_lands_where_it_was_made(page, app):
    starter = page.free.starter
    assert starter.isVisibleTo(page) and starter.choice.count() == len(GUIDES)
    starter.choice.setCurrentIndex(starter.choice.findData("rcd_time"))
    assert starter.is_first("rcd_time")
    starter.button.click()
    window = page.guide_window
    assert window is not None and not window.repeat and window.place.is_new
    window.form.identifier.setText("=F1")
    window.form.fields["rcd_type"].setEditText("A")
    window.next.click()
    made = window.place.asset_id
    assert app.db.asset(made)["identifier"] == "=F1"
    assert page.place_target(page.campaign_id) == made
    window.go(MEASURE)
    meter_of(page).simulate_measurement("rcd_time")
    stored = app.service.measurements(page.campaign_id)
    assert [row["asset_id"] for row in stored] == [made]
    assert window.reading is not None
    window.next.click()
    assert page.guide_window is None
    assert not starter.is_first("rcd_time")
    with speaking("de"):
        starter._label()
    assert starter.button.text() == "Nächstes Element …"


def test_a_repeat_only_asks_for_the_element_and_where_new_ones_hang_is_kept(page, app):
    starter = page.free.starter
    starter.choice.setCurrentIndex(starter.choice.findData("rcd_time"))
    starter.button.click()
    first = page.guide_window
    root = app.service.campaign(page.campaign_id)["asset_id"]
    first.parent_chosen.emit(root)
    first.next.click()
    first.go(MEASURE)
    meter_of(page).simulate_measurement("rcd_time")
    first.next.click()
    starter.button.click()
    repeat = page.guide_window
    assert repeat.repeat and repeat.count == 1
    assert page.new_parents[page.campaign_id] == root


def test_the_switch_chooses_the_guide_and_reaches_the_open_window(page):
    starter = page.free.starter
    position = SelectorPosition("RLO", frozenset({"rlo"}), 13)
    page.guide_selector(position)
    assert starter.choice.currentData() == "rlo"
    starter.button.click()
    assert page.guide_window.position == position
    page.pause()
    assert page.guide_window is None
