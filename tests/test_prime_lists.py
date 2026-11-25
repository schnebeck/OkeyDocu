# OkeyDocu - tests/test_prime_lists.py
# l10n: de
# The setting lists of the PROFITEST PRIME: their data, their drawing, their place in the guide.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtTest import QTest

from okeydocu.devices.guide import CONFIGURE, MEASURE
from okeydocu.devices.profitest_prime import screens
from okeydocu.devices.profitest_prime.info import DRIVER_KEY
from okeydocu.devices.profitest_prime.panel import DRAWING
from okeydocu.devices.profitest_prime.setting_lists import (CABLE, LISTS, RCD_DATA, SECTION,
                                                            SWITCHES, setting_list,
                                                            softkey_view)
from okeydocu.devices.screen import LIST_KEYS, SettingList
from okeydocu.l10n import speaking
from okeydocu.ui.front_panel import FrontPanel
from okeydocu.ui.list_art import ROWS, page_of, reading, said, spot_of
from okeydocu.ui.measuring_window import MeasuringWindow

FORM, RATED = RCD_DATA.settings[2], RCD_DATA.settings[3]


def test_every_list_belongs_to_a_softkey_row_of_its_view_and_fits_the_display():
    for (view, key), listing in LISTS.items():
        assert view.softkey(key) is not None
        assert 0 < len(listing.settings) <= ROWS
        for setting in listing.settings:
            assert all(0 < len(page) <= ROWS for page in setting.pages)
            assert setting.pages or setting.typed  # something can be chosen or entered
            assert setting.page_count() >= setting.before + len(setting.pages)
    assert len(LIST_KEYS) < len(DRAWING.softkeys)  # the lowest softkey does nothing in a list


def test_a_list_is_found_by_view_and_softkey_row_only():
    assert setting_list(screens.RLO, screens.LIMITS) is not setting_list(screens.RISO,
                                                                       screens.LIMITS)
    assert setting_list(screens.RLO, screens.OFFSET) is None


def test_pages_not_seen_are_counted_where_they_stand():
    assert (SECTION.before, len(SECTION.pages), SECTION.page_count()) == (1, 1, 2)
    assert (CABLE.before, len(CABLE.pages), CABLE.page_count()) == (0, 1, 2)
    start = setting_list(screens.IMD, screens.IMD_START).settings[0]
    assert (start.before, start.page_count()) == (4, 7)
    assert spot_of(start, start.shown) == (0, 3)  # the value in force, on the page seen


def test_a_softkey_that_switches_the_view_leads_there_and_back():
    for (view, key), there in SWITCHES.items():
        assert view.softkey(key) is not None and there != view
        back = there.keys[view.softkey(key)]
        assert softkey_view(there, back) == view
    assert softkey_view(screens.U, screens.VIEW_U) == screens.U3
    assert softkey_view(screens.U, screens.U_PATH) is None  # that softkey opens a list
    automatic = softkey_view(screens.IMD, screens.IMD_SEQUENCE)
    assert automatic.keys[1].inverted == "AUTO"
    assert setting_list(automatic, screens.IMD_PATH) is setting_list(screens.IMD,
                                                                     screens.IMD_PATH)


def test_values_read_alike_whatever_names_them():
    assert said("IΔN: 30mA") == said("30 mA") and said("B - MI") == said("B-MI")
    assert said("IΔN: 300mA") != said("30 mA")


def test_the_choice_the_element_names_is_found_on_its_page():
    assert page_of(FORM, {"rcd_type": "A"}.get) == (0, "A")
    assert page_of(FORM, {"rcd_type": "AC"}.get) == (1, "AC")
    assert page_of(RATED, {"rated_current": "40 A"}.get) == (0, "IN: 40A")
    assert page_of(RATED, {"rated_current": "125 A"}.get) == (1, "IN: 125A")
    assert page_of(RATED, {"rated_current": "250 A"}.get) == (0, "")  # not among the choices
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
    assert text.count("Liste zeigen") == 3  # RCD data, test current and limits
    assert all(f'href="list:{softkey}"' in text for softkey in (0, 1, 2))


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


# Working a list with its softkeys --------------------------------------------------------

UP, DOWN, THIRD, TAKE = range(4)


def test_the_cursor_moves_among_settings_and_among_choices_and_turns_the_page():
    form = RCD_DATA.at(2)
    assert form.moved(-5).selected == 0 and form.moved(5).selected == 3  # stops at the ends
    among = form.across((0, 0))
    assert among.keys()[THIRD] == "enter" and form.keys()[THIRD] == "right"
    assert among.moved(9).cursor == (0, 9) and among.moved(10).cursor == (1, 0)
    assert among.moved(99).cursor == (1, 1) and among.moved(-1).cursor == (0, 0)


def test_a_confirmed_choice_is_how_the_setting_reads_from_then_on():
    taken = RCD_DATA.at(2).across((0, 0)).moved(2).confirmed()
    assert taken.cursor is None and taken.wording(2) == "B" and taken.wording(0).startswith("IΔN")
    limits = setting_list(screens.RCD_TIME, screens.LIMITS)
    typed = limits.at(1).across().confirmed()  # only a value entered by hand is offered
    assert typed.wording(1) == "ta: <300ms"
    by_hand = setting_list(screens.RLO, screens.LIMITS).across().moved(5).confirmed()
    assert by_hand.wording(0) == "RLO <9,99Ω"


def press(window, index):
    """A click on the softkey `index` of the drawn panel."""
    panel = window.bench.panel
    centre = panel.part_rect(DRAWING.softkeys[index]).center().toPoint()
    QTest.mouseClick(panel, Qt.MouseButton.LeftButton, pos=centre)


def test_the_softkey_beside_a_setting_opens_its_list(window):
    assert "Softkeys im Bild lassen sich drücken" in window.step_text.text()
    press(window, 3)  # a softkey without a row beside it
    assert window.listed is None
    press(window, 0)
    panel = window.bench.panel
    assert panel.screen == RCD_DATA and window.key_press.isVisible()
    assert panel.pointed == ("soft-1", "soft-2", "soft-3", "soft-4")


def test_the_softkeys_work_the_list_as_the_instrument_does(window):
    panel = window.bench.panel
    press(window, 0)
    press(window, DOWN)
    press(window, DOWN)  # the form of the RCD
    press(window, THIRD)  # to its choices: the cursor stands on what the RCD states
    assert panel.screen.cursor == (0, 0) and panel.screen.keys()[THIRD] == "enter"
    press(window, DOWN)
    press(window, DOWN)
    press(window, THIRD)  # confirmed: back on the settings
    assert panel.screen.cursor is None and panel.screen.wording(2) == "B"
    press(window, TAKE)
    assert window.listed is None and panel.screen == screens.RCD_TIME
    assert window.display_stated("rcd_type") == "B"  # the view shows what was set
    assert window.place.stated("rcd_type") == "A"  # the element states what it did
    press(window, 0)
    assert panel.screen.wording(2) == "B"  # and the list remembers it


def test_taking_over_confirms_the_choice_under_the_cursor(window):
    press(window, 0)
    press(window, THIRD)
    press(window, DOWN)
    press(window, DOWN)
    press(window, DOWN)  # from 30 mA to 200 mA
    press(window, TAKE)
    assert window.display_stated("rated_residual_current") == "200mA"


def test_a_click_beside_the_softkeys_and_at_another_station_does_nothing(window):
    panel = window.bench.panel
    QTest.mouseClick(panel, Qt.MouseButton.LeftButton,
                     pos=panel.part_rect("lcd").center().toPoint())
    assert window.listed is None
    window.go_to(MEASURE)
    press(window, 0)
    assert window.listed is None and not isinstance(panel.screen, SettingList)


def test_a_list_opens_on_the_page_of_the_value_in_force():
    path = setting_list(screens.U, screens.U_PATH)
    assert spot_of(path.settings[0], reading(path, 0, None)) == (1, 0)  # AUTO, on page two
    time = setting_list(screens.RLO, screens.TIME)
    assert spot_of(time.settings[0], reading(time, 0, None)) == (0, 0)
    limits = setting_list(screens.RCD_TIME, screens.LIMITS)
    assert spot_of(limits.settings[1], reading(limits, 1, None)) == (0, 0)  # entered by hand
    stated = {"rcd_type": "AC", "rated_residual_current": "30 mA"}.get
    assert spot_of(FORM, reading(RCD_DATA, 2, stated)) == (1, 1)
    assert spot_of(FORM, reading(RCD_DATA, 2, None)) is None  # the element says nothing


def test_the_cursor_passes_to_the_value_in_force_and_back_over_the_page(qtbot, app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    campaign = app.service.create(machine, "Prüfung", "Tester")
    with speaking("de"):
        shown = MeasuringWindow(app, campaign, DRIVER_KEY, "u", machine)
        qtbot.addWidget(shown)
        shown.show()
        shown.go_to(CONFIGURE)
        press(shown, DRAWING.softkeys.index("soft-4"))  # the measuring path
        panel = shown.bench.panel
        assert isinstance(panel.screen, SettingList)
        press(shown, THIRD)
        assert panel.screen.cursor == (1, 0)  # on AUTO, the only row of page two
        press(shown, UP)
        assert panel.screen.cursor == (0, 9)  # back onto page one
        press(shown, DOWN)
        press(shown, DOWN)
        assert panel.screen.cursor == (1, 0)
        press(shown, TAKE)
        press(shown, 0)  # the top softkey switches between one voltage and the three
        assert panel.screen == screens.U3 and shown.listed is None
        press(shown, 3)  # the three-phase view has no measuring path to list
        assert panel.screen == screens.U3
        press(shown, 0)
        assert panel.screen == screens.U
        press(shown, 0)
        shown.go_to(MEASURE)
        shown.go_to(CONFIGURE)
        assert panel.screen == screens.U  # a switched view ends with the station
