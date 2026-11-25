# OkeyDocu - tests/test_testproject.py
# l10n: de
# The test project: its own data folder, its simulated instrument, the guide played on screen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu import testprojects
from okeydocu.__main__ import options
from okeydocu.devices import driver_info, find_instruments, registry
from okeydocu.devices.guide import MEASURE
from okeydocu.devices.profitest_prime.guides import GUIDES
from okeydocu.devices.profitest_prime.simulated import KEY, SimulatedPrime
from okeydocu.l10n import speaking
from okeydocu.paths import data_dir


@pytest.fixture(autouse=True)
def own_drivers(monkeypatch):
    """The instrument a test project registers leaves with the test."""
    registry.available_drivers()
    monkeypatch.setattr(registry, "_DRIVERS", dict(registry._DRIVERS))


def test_the_command_line_names_a_test_project_and_leaves_qt_its_own_options():
    asked = options(["--testproject", "prime", "--fresh", "-style", "Breeze"])
    assert (asked.testproject, asked.fresh) == ("prime", True)
    assert options([]).testproject is None
    with pytest.raises(SystemExit):
        options(["--testproject", "unknown"])


def test_a_test_project_works_in_a_folder_of_its_own(tmp_path, monkeypatch):
    monkeypatch.setenv("OKEYDOCU_DATA", str(tmp_path / "real"))
    target = testprojects.enter("prime")
    assert target == tmp_path / "real" / "testprojects" / "prime"
    assert data_dir() == target  # from here on the program works there
    (target / "kept.txt").write_text("x", encoding="utf-8")
    monkeypatch.setenv("OKEYDOCU_DATA", str(tmp_path / "real"))
    testprojects.enter("prime")
    assert (target / "kept.txt").exists()  # kept from start to start
    monkeypatch.setenv("OKEYDOCU_DATA", str(tmp_path / "real"))
    testprojects.enter("prime", fresh=True)
    assert not (target / "kept.txt").exists()
    with pytest.raises(ValueError):
        testprojects.enter("unknown")


def test_the_project_is_laid_out_once_and_measures_with_the_simulated_instrument(app):
    with speaking("de"):
        testprojects.prepare(app, "prime")
        testprojects.prepare(app, "prime")
    campaigns = app.service.campaigns()
    assert sorted(row["title"] for row in campaigns) == ["Erstprüfung Bandsäge",
                                                        "Jahresprüfung 2026"]
    assert {row["driver"] for row in campaigns} == {KEY}
    annual = next(row for row in campaigns if row["title"] == "Jahresprüfung 2026")
    assert len(app.service.measurements(annual["id"])) == 5
    assert len(app.service.plan_blocks(annual["id"])) == 1
    assert app.service.key_store is None  # the password store is left alone
    assert driver_info(KEY).simulated and driver_info("profitest-prime") is not None
    assert [found.key for found in find_instruments() if found.key == KEY] == [KEY]


def test_the_simulated_instrument_has_the_dial_and_the_functions_of_the_real_one():
    meter = SimulatedPrime(seed=1)
    with pytest.raises(Exception):
        meter.read_selector()  # nobody has turned it yet
    meter.turn(18)
    assert meter.read_selector().value == 18
    taken = meter.simulate_measurement("zloop_dc")
    assert taken.function == "zloop_dc" and taken.result("zloop") is not None
    assert meter.read_selector().value == GUIDES["zloop_dc"].selector
    assert set(meter.simulated_functions) <= set(GUIDES)
    assert meter.identify().manufacturer == "Simulator"  # never taken for a real instrument


def test_the_guide_is_played_on_the_screen(window, app, qtbot):
    with speaking("de"):
        testprojects.prepare(app, "prime")
        first = next(row["id"] for row in app.service.campaigns()
                     if row["title"] == "Erstprüfung Bandsäge")
        page = window.campaign
        page.refresh()
        page.enter(first)
        assert page.free.simulate_function.findData("zloop_dc") >= 0
        page.open_guide("rlo")
        guide = page.guide_window
        assert guide.simulated and not guide.simulate.isVisible()
        guide.form.panel.tree.select(app.service.campaign(first)["asset_id"])
        guide.dial_turned.emit(GUIDES["rlo"].selector)
        assert guide.position is not None and guide.position.value == GUIDES["rlo"].selector
        guide.go_to(MEASURE)
        assert guide.simulate.isVisible()
        guide.simulate.click()
        qtbot.waitUntil(lambda: "rlo" in guide.bench.panel.values)
        assert [row["function"] for row in app.service.measurements(first)] == ["rlo"]
        page.close_guide()
