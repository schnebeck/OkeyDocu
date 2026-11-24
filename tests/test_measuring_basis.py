# OkeyDocu - tests/test_measuring_basis.py
# Every guided function names its standards, why it is taken and where to measure next.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import re

from okeydocu.devices.guide import CONFIGURE
from okeydocu.devices.profitest_prime.guides import GUIDES
from okeydocu.l10n import speaking
from okeydocu.ui.measuring_window import MeasuringWindow
from okeydocu.ui.station_texts import basis_text, further_text
from okeydocu.vocabulary.basis import bases, basis_of
from okeydocu.vocabulary.terms import vocabulary

from .test_prime_guides import opened


def guided_functions() -> set[str]:
    found = set(GUIDES)
    for guide in GUIDES.values():
        found |= {variant.guide.function for variant in guide.variants}
    return found


def test_every_guided_function_has_a_full_basis():
    for function in guided_functions():
        basis = basis_of(function)
        assert basis is not None, function
        assert basis.standards and basis.why and basis.further, function


def test_a_basis_belongs_to_a_function_of_the_vocabulary():
    assert set(bases()) <= set(vocabulary().functions)


def test_standards_are_codes_that_read_the_same_in_every_language():
    for function in guided_functions():
        for standard in basis_of(function).standards:
            assert not re.search(r"[a-zäöüß]{2}", standard), standard


def test_the_texts_follow_the_language():
    with speaking("de"):
        assert "Grundlage:" in basis_text("zloop")
        assert "EN 60204-1 (VDE 0113-1): 18.2.3, A.1" in basis_text("zloop")
        assert "Weiter messen:" in further_text("zloop")
        assert "Ende jedes Stromkreises" in further_text("zloop")
    assert basis_text("no_such_function") == further_text("no_such_function") == ""


def test_mode_and_limits_show_what_the_measurement_rests_on(qtbot, app):
    window = opened(qtbot, app, "riso")
    index = next(i for i, station in enumerate(window.guide.flow) if station.kind == CONFIGURE)
    with speaking("de"):
        window.go(index)
        text = window.step_text.text()
    assert "Grundlage:" in text and "EN 60204-1 (VDE 0113-1): 18.3" in text
    assert "1 MΩ" in text


def test_a_loop_method_warns_where_the_rcd_type_rules_it_out(qtbot, app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    rcd = app.db.add_asset(customer, "rcd", "F1", parent_id=machine)
    app.db.set_asset_features(rcd, {"rcd_type": "B"})
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    with speaking("de"):
        texts = {}
        for function in ("zloop_dc", "zloop_half", "zloop_rlo"):
            window = MeasuringWindow(app, campaign, "profitest-prime", function, rcd)
            qtbot.addWidget(window)
            window.go(next(i for i, s in enumerate(window.guide.flow) if s.kind == CONFIGURE))
            texts[function] = window.step_text.text()
    assert "Typ B erkennt den Gleichstrom" in texts["zloop_dc"]
    assert "nur für die Typen A und F" in texts["zloop_half"]
    assert "Typ B erkennt" not in texts["zloop_rlo"]
    assert "nur für die Typen" not in texts["zloop_rlo"]
