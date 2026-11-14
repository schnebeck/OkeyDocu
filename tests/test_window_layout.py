# OkeyDocu - tests/test_window_layout.py
# The window around the work: status bar, menus, panels and what survives a restart.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtWidgets import QApplication

from okeydocu.ui.board import GUTTER
from okeydocu.ui.main_window import MainWindow

from .workspace_helpers import plan_title, record, start, with_asset


def test_status_stays_in_sight_in_the_status_bar(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch, simulated=True)
    bar = window.statusBar()
    assert window.campaign.link.parent() is bar
    assert window.campaign.clock.parent() is bar
    assert window.campaign.link.isVisible()
    assert not window.campaign.clock.isVisible()  # set at the start, so nothing to report
    window.open_page(window.measurements)
    assert window.campaign.link.isVisible()


def test_menus_name_the_work(window):
    titles = [action.text().replace("&", "") for action in window.menuBar().actions()]
    assert titles == [
        "Kampagne", "Bearbeiten", "Ansicht", "Messgerät", "Daten", "Einstellungen", "Hilfe",
    ]


def test_menu_entries_follow_the_state_of_the_campaign(window, app, monkeypatch):
    page = window.campaign
    assert not page.finish_action.isEnabled()
    assert not page.report_action.isEnabled()
    with_asset(window, app)
    start(window, monkeypatch)
    assert not page.finish_action.isEnabled()  # nothing recorded: deleted, not confirmed
    record(window, app)
    assert page.finish_action.isEnabled()
    assert not page.report_action.isEnabled()
    assert not page.clock_action.isEnabled()  # typed in by hand, there is no instrument
    assert page.values.manual_action.isEnabled()


def test_panels_can_be_hidden_and_come_back_the_same(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    window.side_action.setChecked(False)
    assert not window.campaign.side.isVisible()
    window.close()
    again = MainWindow(app)
    qtbot.addWidget(again)
    again.show()
    assert not again.side_action.isChecked()
    assert not again.campaign.side.isVisible()
    assert not again.list_action.isChecked()  # the list waits at the edge
    assert not again.campaign.list.isVisible()


def reopened(qtbot, app, window):
    window.close()
    again = MainWindow(app)
    qtbot.addWidget(again)
    again.show()
    return again


def drag(splitter, sizes):
    """Moving a handle by hand reports the move, setting the sizes does not."""
    splitter.setSizes(sizes)
    splitter.splitterMoved.emit(sizes[0], 1)


def test_window_fits_a_small_laptop_in_every_state(window, app, monkeypatch):
    """1366 x 768, less the desktop panel and the title bar."""
    assert window.minimumSizeHint().width() <= 1200
    assert window.minimumSizeHint().height() <= 680
    with_asset(window, app)
    start(window, monkeypatch, plan_title(window), simulated=True)
    assert window.minimumSizeHint().width() <= 1200
    assert window.minimumSizeHint().height() <= 680
    window.resize(1200, 680)
    assert (window.width(), window.height()) == (1200, 680)


def test_window_size_survives_a_restart(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    window.resize(1111, 666)
    again = reopened(qtbot, app, window)
    assert (again.width(), again.height()) == (1111, 666)


def test_panel_widths_survive_a_restart(qtbot, app, monkeypatch):
    app.db.add_asset(app.db.add_customer("Muster AG"), "installation", "Halle 1")
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    campaign = app.service.create(app.db.assets()[0]["id"], "T", "P")
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    window.list_action.setChecked(True)
    drag(window.campaign.splitter, [333, 1000])
    drag(window.campaign.running, [700, 300])
    wanted = window.campaign.running.sizes()
    again = reopened(qtbot, app, window)
    again.campaign.refresh()
    again.campaign.show_campaign(campaign)
    assert again.campaign.splitter.sizes()[0] == 333
    assert abs(again.campaign.running.sizes()[1] - wanted[1]) <= 2


def test_a_stored_width_does_not_bring_back_an_old_gap(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.campaign.splitter.setHandleWidth(3)  # as a state stored by an older layout has it
    drag(window.campaign.splitter, [300, 1000])
    again = reopened(qtbot, app, window)
    assert again.campaign.splitter.handleWidth() == GUTTER


def test_a_pinned_list_comes_back_pinned_with_its_width(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    window.list_action.setChecked(True)
    drag(window.campaign.splitter, [300, 1000])
    again = reopened(qtbot, app, window)
    assert again.list_action.isChecked() and again.campaign.list.isVisible()
    QApplication.processEvents()
    assert again.campaign.splitter.sizes()[0] >= 290
    again.list_action.setChecked(False)
    assert not again.campaign.list.isVisible()


def test_folded_sections_stay_folded(qtbot, app, monkeypatch):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    window.campaign.photo_section.toggle.click()
    again = reopened(qtbot, app, window)
    assert not again.campaign.photo_section.expanded
    assert again.campaign.asset_section.expanded


def test_own_windows_keep_their_size(qtbot, app):
    window = MainWindow(app)
    qtbot.addWidget(window)
    window.show()
    window.open_page(window.templates)
    window.page_windows[window.templates].resize(1001, 601)
    again = reopened(qtbot, app, window)
    size = again.page_windows[again.templates].size()
    assert (size.width(), size.height()) == (1001, 601)


def test_nothing_can_be_edited_before_a_campaign_is_chosen(window):
    values = window.campaign.values
    for action in (values.manual_action, values.edit_action, values.delete_action):
        assert not action.isEnabled()


def test_folding_a_section_hides_its_content(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    section = window.campaign.asset_section
    section.toggle.click()
    assert not section.content.isVisible()
    section.toggle.click()
    assert section.content.isVisible()


def test_closing_the_main_window_closes_the_others(window):
    window.open_page(window.templates)
    assert window.templates.isVisible()
    window.close()
    assert not window.templates.isVisible()


def test_quitting_says_that_the_program_ends(window):
    assert window.quit_action.text() == "OkeyDocu beenden"


def test_a_restart_begins_on_the_start_screen(qtbot, app, window, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    again = reopened(qtbot, app, window)
    assert again.campaign.pages.currentWidget() is again.campaign.home
    assert again.campaign.home.cards[0].summary.title == "Prüfung Halle"
    assert again.campaign.session is None  # nothing connects by itself


def test_a_column_width_set_by_hand_comes_back(qtbot, app, window):
    header = window.campaign.values.table.horizontalHeader()
    header.resizeSection(4, 333)
    again = reopened(qtbot, app, window)
    assert again.campaign.values.table.horizontalHeader().sectionSize(4) == 333


def test_a_page_window_closes_by_button_and_keys(qtbot, window):
    from PySide6.QtCore import Qt

    window.open_page(window.master_data)
    page_window = window.page_windows[window.master_data]
    assert page_window.isVisible()
    page_window.close_button.click()
    assert not page_window.isVisible()
    window.open_page(window.master_data)
    qtbot.keyClick(page_window, Qt.Key.Key_Escape)
    assert not page_window.isVisible()
