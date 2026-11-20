# OkeyDocu - tests/test_prime_screens.py
# The PROFITEST PRIME's display views: one per switch position, drawn beside the softkeys.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QRectF

from okeydocu.devices.guide import CONFIGURE, MEASURE, PLACE, PREPARE
from okeydocu.devices.profitest_prime import screens
from okeydocu.devices.profitest_prime.guides import GUIDES as PRIME
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.devices.profitest_prime.panel import DRAWING
from okeydocu.devices.profitest_prime.selector import selector_position
from okeydocu.l10n import speaking
from okeydocu.ui.front_panel import FrontPanel
from okeydocu.ui.measuring_window import MeasuringWindow
from okeydocu.ui.screen_art import INK
from okeydocu.ui.station_kinds import parts_of

THREE_PHASE = PRIME["u"].variants[0].guide
GUIDED = (*PRIME.values(), THREE_PHASE, THREE_PHASE.follow)
VIEWS = [view for views in screens.AT_POSITION.values() for view in views]


def test_every_view_has_a_row_for_each_softkey_and_a_position_the_instrument_reports():
    for view in VIEWS:
        assert len(view.keys) == len(DRAWING.softkeys)
        assert len(view.rows) == len(DRAWING.softkeys) - 1
    assert all(selector_position(value).label for value in screens.AT_POSITION)


def test_every_setting_named_by_a_softkey_row_is_on_a_view_the_guide_shows():
    for guide in GUIDED:
        views = (guide.screen, *(view for _, view in guide.screens))
        named = [action.key for action in guide.settings if action.key is not None]
        assert named and all(any(view.softkey(key) is not None for view in views)
                             for key in named), guide.function
        assert all(any(view.softkey(key) is not None for key in named) for view in views)
        shares = [part for part in parts_of(guide.steps) if part in DRAWING.softkeys]
        measured = guide.screen_at(None, measured=True)
        assert [measured.keys[DRAWING.softkeys.index(part)] for part in shares] == [screens.SHARE]


def test_the_views_a_guide_shows_are_those_of_the_positions_that_serve_it():
    for guide in GUIDED:
        assert guide.screen in screens.AT_POSITION[guide.selector]
        for value, view in guide.screens:
            assert view in screens.AT_POSITION[value]
            assert guide.function in selector_position(value).functions


def ink(panel: FrontPanel, area: QRectF) -> int:
    """Dark dots of the display's ink inside `area` of the panel as painted."""
    image = panel.grab().toImage()
    return sum(image.pixelColor(x, y) == INK
               for x in range(int(area.left()), int(area.right()))
               for y in range(int(area.top()), int(area.bottom())))


@pytest.fixture
def panel(qtbot):
    widget = FrontPanel(DRAWING)
    qtbot.addWidget(widget)
    widget.resize(1040, 725)
    widget.view = QRectF(455, 462, 320, 170)
    return widget


def test_the_display_is_dark_until_a_view_is_shown(panel):
    display = panel.part_rect("lcd")
    assert ink(panel, display) == 0
    panel.show_screen(screens.RLO)
    assert ink(panel, display) > 500
    panel.show_screen(None)
    assert ink(panel, display) == 0


def test_a_softkeys_label_stands_at_the_height_of_its_key(panel):
    panel.show_screen(screens.RLO_25A)  # the first and the last softkey do nothing here
    display = panel.part_rect("lcd")
    inner = QRectF(display.right() - display.width() * 0.2, 0, display.width() * 0.15, 0)
    labelled = []
    for key in DRAWING.softkeys:
        centre = panel.part_rect(key).center().y()
        band = QRectF(inner.left(), centre - 12, inner.width(), 24)
        labelled.append(ink(panel, band) > 0)
    assert labelled == [False, True, True, True, False]


def test_a_softkey_row_shows_what_the_element_states(panel):
    panel.show_screen(screens.RCD_TIME, {"rated_residual_current": "30 mA"}.get)
    first = panel.grab().toImage()
    panel.show_screen(screens.RCD_TIME, {"rated_residual_current": "300 mA"}.get)
    assert panel.grab().toImage() != first


def test_the_display_follows_the_stations(qtbot, app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    campaign = app.service.create(machine, "Prüfung", "Tester")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, DRIVER_KEY, "rlo", machine)
    qtbot.addWidget(window)
    window.show()
    shown = window.bench.panel
    assert window.kind == PLACE and shown.screen is None
    for kind, view in ((PREPARE, screens.RLO), (CONFIGURE, screens.RLO),
                       (MEASURE, screens.RLO.with_key(*screens.RESULT)),
                       (CONFIGURE, screens.RLO)):
        window.go_to(kind)
        assert shown.screen == view, kind


def test_display_and_softkeys_follow_the_position_the_instrument_stands_at(qtbot, app):
    """IΔN and IF+IΔN both serve the tripping test, with the RCD data in different rows."""
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    rcd = app.db.add_asset(customer, "rcd", "FI Steuerung", machine)
    campaign = app.service.create(machine, "Prüfung", "Tester")
    with speaking("de"):
        window = MeasuringWindow(app, campaign, DRIVER_KEY, "rcd_time", rcd)
        qtbot.addWidget(window)
        window.show()
        window.go_to(CONFIGURE)
        assert window.bench.panel.screen == screens.RCD_TIME
        assert window.bench.panel.pointed == ("soft-1", "soft-2", "soft-3")
        assert "Prüfstrom" in window.step_text.text()
        window.show_selector(selector_position(19))
        window.go_to(CONFIGURE)
        assert window.bench.panel.screen == screens.RCD_BOTH
        assert window.bench.panel.pointed == ("soft-2", "soft-3")
        assert "Prüfstrom" not in window.step_text.text()
        window.show_selector(selector_position(13))
        window.go_to(CONFIGURE)
    assert window.bench.panel.screen == screens.RCD_TIME
