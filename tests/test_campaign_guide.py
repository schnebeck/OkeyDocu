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
    window.go_to(MEASURE)
    meter_of(page).simulate_measurement("rcd_time")
    stored = app.service.measurements(page.campaign_id)
    assert [row["asset_id"] for row in stored] == [made]
    assert window.reading is not None
    window.next.click()
    assert page.guide_window is None
    assert not starter.is_first("rcd_time")
    with speaking("de"):
        starter._label()
    assert starter.button.text() == "Geführt wiederholen …"


def test_a_repeat_runs_the_stations_again_and_where_new_ones_hang_is_kept(page, app):
    starter = page.free.starter
    starter.choice.setCurrentIndex(starter.choice.findData("rcd_time"))
    starter.button.click()
    first = page.guide_window
    root = app.service.campaign(page.campaign_id)["asset_id"]
    first.parent_chosen.emit(root)
    first.next.click()
    first.go_to(MEASURE)
    meter_of(page).simulate_measurement("rcd_time")
    first.next.click()
    starter.button.click()
    repeat = page.guide_window
    assert repeat.repeat and repeat.count == len(repeat.flow) > 1
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


def test_a_position_serving_several_guides_chooses_the_one_that_leads_to_it(page):
    """IF+IΔN also produces the readings of the tripping time and of the tripping current."""
    from okeydocu.devices.profitest_prime.selector import selector_position

    starter = page.free.starter
    for value, function in ((19, "i_ramp"), (18, "rcd_time"), (17, "rcd_current"),
                            (20, "zloop"), (21, "zloop_dc"), (22, "zloop_rlo"),
                            (23, "zloop_half"), (16, "riso_ramp"), (25, "imd"),
                            (26, "rcm_touch"), (27, "il"), (28, "i_clamp"), (30, "zln_du"),
                            (24, "ures")):
        page.guide_selector(selector_position(value))
        assert starter.choice.currentData() == function
    page.guide_selector(selector_position(33))
    assert starter.choice.currentData() == "ures"
