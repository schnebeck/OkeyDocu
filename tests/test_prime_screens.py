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


def test_every_softkey_a_guide_points_at_has_a_label_on_the_view_it_shows():
    for guide in GUIDED:
        for part in parts_of(guide.settings):
            assert guide.screen.keys[DRAWING.softkeys.index(part)] is not None, guide.function
        shares = [part for part in parts_of(guide.steps) if part in DRAWING.softkeys]
        assert [guide.result_screen.keys[DRAWING.softkeys.index(part)] for part in shares] \
            == [screens.SHARE]
        assert guide.screen.keys[screens.SHARE_KEY] is None


def test_the_view_a_guide_shows_is_one_of_its_switch_position():
    for guide in GUIDED:
        assert guide.screen in screens.AT_POSITION[guide.selector]


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
                       (MEASURE, screens.shared(screens.RLO)), (CONFIGURE, screens.RLO)):
        window.go_to(kind)
        assert shown.screen == view, kind
