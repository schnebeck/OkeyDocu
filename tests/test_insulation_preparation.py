# OkeyDocu - tests/test_insulation_preparation.py
# What the guide says about switches before the insulation is measured.
# l10n: de
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.devices.guide import CONNECT
from okeydocu.l10n import speaking, tr
from okeydocu.ui.measuring_window import MeasuringWindow


@pytest.fixture
def machine(app):
    customer = app.db.add_customer("Muster AG")
    return app.db.add_asset(customer, "machine", "Presse")


@pytest.mark.parametrize("connection", ["CEE plug", "fixed"])
def test_every_switch_is_closed_before_the_insulation_is_measured(qtbot, app, machine,
                                                                  connection):
    app.db.set_asset_features(machine, {"supply_connection": connection})
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    window = MeasuringWindow(app, campaign, "profitest-prime", "riso", machine)
    qtbot.addWidget(window)
    with speaking("de"):
        steps = {tr(heading): tr(text) for heading, text in window.guide.preparation}
    said = steps["Hauptschalter und alle Schutzschalter einschalten"]
    assert "Leitungsschutzschalter" in said and "Schütz" in said


def test_the_preparation_is_recalled_where_the_probes_are_placed(qtbot, app, machine):
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, "profitest-prime", "riso", machine)
        qtbot.addWidget(window)
        window.go(next(i for i, s in enumerate(window.guide.flow) if s.kind == CONNECT))
        text = window.step_text.text()
    assert "<b>Vorbereitet?</b>" in text
    assert "Hauptschalter und alle Schutzschalter einschalten" in text


def test_measuring_says_that_only_the_pairs_against_pe_count(qtbot, app, machine):
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, "profitest-prime", "riso", machine)
        qtbot.addWidget(window)
        text = window.measure_text()
    assert "Es zählt nur ein Leiter gegen PE: L1-PE, L2-PE, L3-PE, N-PE (EN 60204-1, 18.3)" in text
    assert "den Stromkreis eingeschaltet lassen" in text


@pytest.mark.parametrize("function", ["zloop_dc", "zloop_rlo"])
def test_a_loop_behind_an_rcd_says_which_pairs_are_loops(qtbot, app, machine, function):
    rcd = app.db.add_asset(app.db.asset(machine)["customer_id"], "rcd", "F1", parent_id=machine)
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, "profitest-prime", function, rcd)
        qtbot.addWidget(window)
        text = window.measure_text()
    assert "Eine Schleife ist nur ein Außenleiter gegen PE: L1-PE, L2-PE, L3-PE." in text
    assert "mit IΔN überspringen" in text and "Stellung ZLOOP mit zwei Prüfspitzen" in text
