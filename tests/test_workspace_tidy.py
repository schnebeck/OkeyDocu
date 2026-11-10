# EasyMeasurement - tests/test_workspace_tidy.py
# The calm workspace: the list at the edge, row actions in the menu, checks in the head.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest
from PySide6.QtCore import QPoint

from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.ui.campaign_checks import FAILED_LINK, UNPLACED_LINK
from easymeasurement.ui.edge_drawer import LEAVE_POLLS
from easymeasurement.ui.move_overlay import MoveOverlay
from easymeasurement.ui.structure_tree import UNPLACED


def _value(text, verdict=Verdict.PASSED):
    return ResultValue("riso", "RISO", Quantity.parse(text), verdict, ">1MΩ", "")


@pytest.fixture
def shown(window, app):
    customer = app.db.add_customer("Muster AG")
    press = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=press)
    campaign = app.service.create(press, "Prüfung", "Prüfer")
    for text, verdict, place in (("2MΩ", Verdict.PASSED, cabinet),
                                 ("0.2MΩ", Verdict.FAILED, cabinet),
                                 ("3MΩ", Verdict.PASSED, None)):
        app.service.add_measurement(campaign, "riso", [_value(text, verdict)],
                                    datetime(2026, 5, 4, 9), verdict, asset_id=place)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return {"page": page, "press": press, "cabinet": cabinet, "campaign": campaign}


def test_the_list_waits_at_the_edge_and_goes_when_the_mouse_leaves(window):
    drawer = window.campaign.drawer
    assert not drawer.isVisible()
    drawer.react(QPoint(300, 200))
    assert not drawer.isVisible()  # only the edge opens it
    drawer.react(QPoint(2, 200))
    assert drawer.shown()
    for _ in range(LEAVE_POLLS):
        drawer.react(QPoint(900, 200))
    assert not drawer.shown()


def test_a_pinned_list_does_not_slide(window):
    window.list_action.setChecked(True)
    window.campaign.drawer.react(QPoint(2, 200))
    assert not window.campaign.drawer.isVisible()
    assert window.campaign.splitter.indexOf(window.campaign.list) == 0
    assert not window.drawer_action.isEnabled()


def test_the_head_counts_what_is_left_and_leads_there(shown):
    page = shown["page"]
    checks = page.header.checks.text()
    assert "1 ohne Ort" in checks and "1 Mangel" in checks
    page._follow_check(UNPLACED_LINK)
    assert page.structure.current_id() == UNPLACED
    page._follow_check(FAILED_LINK)
    assert page.structure.current_id() == shown["cabinet"]
    assert page.values.table.currentItem() is not None
    row = page.values.table.currentRow()
    assert page.values.table.item(row, 8).text() == "nicht bestanden"


def test_rows_are_moved_by_choosing_an_element(shown, app, monkeypatch):
    page = shown["page"]
    page.structure.select(UNPLACED)
    page.values.table.selectRow(0)
    assert page.values.move_action.isEnabled()
    monkeypatch.setattr(MoveOverlay, "exec", lambda overlay: 1)
    monkeypatch.setattr(MoveOverlay, "chosen", lambda overlay: shown["cabinet"])
    page.values.move_action.trigger()
    assert "ohne Ort" not in page.header.checks.text()


def test_the_overlay_offers_the_installation(shown, app):
    overlay = MoveOverlay(app, shown["press"], 2, shown["cabinet"])
    assert overlay.chosen() == shown["cabinet"]
    overlay.search.setText("nirgends")
    assert overlay.items[shown["press"]].isHidden()


def test_the_filter_narrows_the_table(shown, qtbot):
    values = shown["page"].values
    shown["page"].structure.select(shown["press"])
    assert values.table.rowCount() == 3  # the whole campaign
    values.find.setText("0.2")
    qtbot.waitUntil(lambda: values.table.rowCount() == 1)


def test_empty_sections_say_so_in_a_line(shown):
    page = shown["page"]
    page.values.table.clearSelection()
    page.values.table.setCurrentItem(None)
    page.values._show_detail()
    assert page.detail_section.empty and page.photo_section.empty
    page.values.table.selectRow(0)
    assert not page.detail_section.empty
    assert "Keine Fotos" in page.photo_section.placeholder.text()


def test_answers_come_before_their_questions(window, app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    values = [ResultValue("question", "Prüffrage", Quantity(raw="Schutz vorhanden?")),
              ResultValue("answer", "Antwort", Quantity(raw="yes"))]
    app.service.add_measurement(campaign, "visual_inspection", values,
                                datetime(2026, 5, 4, 9), Verdict.PASSED)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    assert page.values.table.item(0, 6).text() == "ja – Schutz vorhanden?"
    assert not page.values.table.item(0, 0).icon().isNull()
