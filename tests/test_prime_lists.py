# OkeyDocu - tests/test_prime_lists.py
# l10n: de
# The setting lists of the PROFITEST PRIME: their data, their drawing, their place in the guide.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QRectF

from okeydocu.devices.guide import CONFIGURE, MEASURE
from okeydocu.devices.profitest_prime import screens
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.devices.profitest_prime.panel import DRAWING
from okeydocu.devices.profitest_prime.setting_lists import LISTS, RCD_DATA, setting_list
from okeydocu.devices.screen import LIST_KEYS, SettingList
from okeydocu.l10n import speaking
from okeydocu.ui.front_panel import FrontPanel
from okeydocu.ui.list_art import ROWS, page_of, said
from okeydocu.ui.measuring_window import MeasuringWindow

FORM, RATED = RCD_DATA.settings[2], RCD_DATA.settings[3]


def test_every_list_belongs_to_a_softkey_row_of_its_view_and_fits_the_display():
    for (view, key), listing in LISTS.items():
        assert view.softkey(key) is not None
        assert 0 < len(listing.settings) <= ROWS
        for setting in listing.settings:
            assert all(0 < len(page) <= ROWS for page in setting.pages)
            assert setting.pages or setting.typed  # something can be chosen or entered
            assert setting.page_count() >= len(setting.pages)
    assert len(LIST_KEYS) < len(DRAWING.softkeys)  # the lowest softkey does nothing in a list


def test_a_list_is_found_by_view_and_softkey_row_only():
    assert setting_list(screens.RLO, screens.LIMITS) is not setting_list(screens.RISO,
                                                                       screens.LIMITS)
    assert setting_list(screens.IMD, screens.IMD_START) is None


def test_values_read_alike_whatever_names_them():
    assert said("IΔN: 30mA") == said("30 mA") and said("B - MI") == said("B-MI")
    assert said("IΔN: 300mA") != said("30 mA")


def test_the_choice_the_element_names_is_found_on_its_page():
    assert page_of(FORM, {"rcd_type": "A"}.get) == (0, "A")
    assert page_of(FORM, {"rcd_type": "AC"}.get) == (1, "AC")
    assert page_of(RATED, {"rated_current": "40 A"}.get) == (0, "IN: 40A")
    assert page_of(RATED, {"rated_current": "125 A"}.get) == (0, "")  # on a page not known
    assert page_of(FORM, None) == (0, "") and RATED.page_count() == 2


def test_every_list_can_be_drawn_with_each_of_its_settings_selected(qtbot):
    panel = FrontPanel(DRAWING)
    qtbot.addWidget(panel)
    panel.resize(1040, 725)
    panel.view = QRectF(455, 462, 320, 170)
    panel.show_screen(screens.RCD_TIME)
    view = panel.grab().toImage()
    for listing in LISTS.values():
        for index in range(len(listing.settings)):
            panel.show_screen(listing.at(index), {"rcd_type": "AC"}.get)
            assert panel.grab().toImage() != view


@pytest.fixture
def window(qtbot, app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    rcd = app.db.add_asset(customer, "rcd", "FI Steuerung", machine)
    app.db.set_asset_features(rcd, {"rcd_type": "A", "rated_residual_current": "30"})
    campaign = app.service.create(machine, "Prüfung", "Tester")
    with speaking("de"):
        shown = MeasuringWindow(app, campaign, DRIVER_KEY, "rcd_time", rcd)
        qtbot.addWidget(shown)
        shown.show()
        shown.go_to(CONFIGURE)
        yield shown


def test_a_setting_with_a_known_list_offers_to_show_it(window):
    text = window.step_text.text()
    assert text.count("Liste zeigen") == 2  # RCD data and limits; the test current has none
    assert 'href="list:0"' in text and 'href="list:2"' in text and 'href="list:1"' not in text


def test_the_link_steps_through_the_list_and_back_to_the_view(window):
    panel = window.bench.panel
    window.step_text.linkActivated.emit("list:0")
    assert panel.screen == RCD_DATA.at(0) and isinstance(panel.screen, SettingList)
    assert panel.pointed == ("soft-1", "soft-2", "soft-3", "soft-4")
    assert "Weiter in der Liste" in window.step_text.text()
    for selected in (1, 2, 3):
        window.step_text.linkActivated.emit("list:0")
        assert panel.screen.selected == selected
    assert "Zurück zur Messansicht" in window.step_text.text()
    window.step_text.linkActivated.emit("list:0")
    assert panel.screen == screens.RCD_TIME
    assert panel.pointed == ("soft-1", "soft-2", "soft-3")


def test_another_setting_opens_its_own_list_from_the_start(window):
    window.step_text.linkActivated.emit("list:0")
    window.step_text.linkActivated.emit("list:0")
    window.step_text.linkActivated.emit("list:2")
    assert window.bench.panel.screen == setting_list(screens.RCD_TIME, screens.LIMITS).at(0)


def test_leaving_the_station_puts_the_list_away(window):
    window.step_text.linkActivated.emit("list:0")
    window.go_to(MEASURE)
    assert window.listed is None and not isinstance(window.bench.panel.screen, SettingList)
    window.go_to(CONFIGURE)
    assert window.bench.panel.screen == screens.RCD_TIME
