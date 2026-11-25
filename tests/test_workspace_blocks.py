# OkeyDocu - tests/test_workspace_blocks.py
# The blocks of the campaign workspace: closed frames that share their edges.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The head, the line that says what to do now and the board stand below each other. What
they hold begins and ends on the same two lines down the window."""

import pytest
from PySide6.QtCore import QPoint

from okeydocu.l10n import speaking
from okeydocu.ui.board import GUTTER, UNIT, Board
from okeydocu.ui.campaign_values import FIND_WIDTH
from okeydocu.ui.framed import Framed

from .workspace_helpers import record, start, with_asset


@pytest.fixture
def page(window, app, monkeypatch, qtbot):
    with_asset(window, app)
    with speaking("de"):
        start(window, monkeypatch, simulated=True)
        record(window, app)
    window.resize(1500, 800)
    qtbot.wait(50)
    return window.campaign


def left(widget, page) -> int:
    return widget.mapTo(page, QPoint(0, 0)).x()


def right(widget, page) -> int:
    return left(widget, page) + widget.width()


def test_the_head_gives_each_detail_a_line_of_its_own(page):
    details = page.header.details.text()
    assert details.count("<tr>") == 4
    for name in ("Kunde", "Anlage", "Prüfer", "Messplan"):
        assert f">{name}</td>" in details
    assert "Muster AG" in details and "Halle 1" in details


def top(widget, page) -> int:
    return widget.mapTo(page, QPoint(0, 0)).y()


def test_head_and_what_to_do_now_are_blocks_as_wide_as_the_board(page):
    for block in (page.header, page.free):
        assert isinstance(block, Framed)
        assert left(block, page) == left(page.board, page)
        assert right(block, page) == right(page.board, page)


def test_head_row_and_board_are_the_rows_of_one_table(page):
    """One frame around all three, a line between them and no room."""
    assert top(page.free, page) == top(page.header, page) + page.header.height()
    assert top(page.board, page) == top(page.free, page) + page.free.height()
    assert page.header.top and page.header.joined
    assert not page.free.top and page.free.joined
    assert not page.board.top


def test_the_board_keeps_its_place_when_measuring_pauses(page, qtbot):
    before = top(page.board, page)
    assert page.current_work() is page.free
    page.header.pause_button.click()
    qtbot.wait(50)
    with speaking("de"):
        page.refresh()
    assert page.free.isVisible() and not page.free.leading
    assert page.free.guidance.text() == "Die Messung ist unterbrochen."
    assert not page.free.starter.isVisible()
    assert not page.free.instruction_action.isEnabled()
    assert page.current_work() is None
    assert top(page.board, page) == before


def test_the_actions_and_the_filter_end_on_one_line(page):
    assert right(page.header.actions, page) == right(page.values.find, page)
    assert right(page.free.starter, page) == right(page.values.find, page)


def test_the_filter_begins_where_the_draft_button_begins(page):
    assert left(page.values.find, page) == left(page.header.draft_button, page)


def test_the_filter_keeps_a_width_of_its_own_without_two_actions_above(page, qtbot):
    assert page.header.span(99) is None
    page.values.align_filter(page.header.span(99))
    qtbot.wait(50)
    assert page.values.find.width() == FIND_WIDTH


def test_actions_stand_twice_as_far_apart_as_from_the_frame(page):
    shown = [button for button in page.header.buttons if button.isVisibleTo(page)]
    gaps = {left(after, page) - right(before, page) for before, after in zip(shown, shown[1:])}
    assert gaps == {2 * UNIT}
    assert right(page.header, page) - right(shown[-1], page) == UNIT + 1  # the frame's line


def test_no_line_of_the_board_ends_in_nothing(page):
    """The rule between the panes is a bare line from the head's rule to the frame."""
    assert page.board.splitter.handleWidth() == 1
    assert page.values.head.ruled and page.values.bar.ruled and page.structure_panel.bar.ruled


def test_no_block_touches_the_window_border(page):
    edges = page.layout().contentsMargins()
    assert min(edges.left(), edges.top(), edges.right(), edges.bottom()) > 0


def test_the_photo_timeline_is_a_block_of_its_own(page):
    """A closed frame, as far from the board as the columns are from each other."""
    assert isinstance(page.timeline, Framed) and page.timeline.top and not page.timeline.joined
    assert page.work.handleWidth() == page.running.handleWidth() == GUTTER


def test_the_buttons_on_either_side_of_the_rule_are_a_pair(page):
    assert page.structure_panel.new_button.width() == page.values.manual_button.width()


def test_the_sections_beside_begin_with_the_head(page):
    section = page.asset_section
    assert section.mapTo(page, QPoint(0, 0)).y() == page.header.mapTo(page, QPoint(0, 0)).y()
    edges = section.layout().contentsMargins()
    assert edges.left() == edges.top() == edges.right() == edges.bottom() == UNIT + 1


def test_the_sections_beside_are_the_rows_of_one_table(page, qtbot):
    """No room between them; the first on show begins the frame, each closes it below."""
    shown = [section for section in page.side.sections if not section.isHidden()]
    assert len(shown) > 1
    for above, below in zip(shown, shown[1:]):
        assert top(below, page) == top(above, page) + above.height()
    assert [section.top for section in shown] == [True] + [False] * (len(shown) - 1)
    assert all(section.joined for section in shown)
    shown[0].hide()
    qtbot.wait(50)
    assert shown[1].top
    shown[0].show()
    qtbot.wait(50)
    assert shown[0].top and not shown[1].top


def test_a_running_plan_continues_the_table_with_a_row_of_the_same_height(page):
    boards = page.plan_run.findChildren(Board)
    assert [board.splitter.objectName() for board in boards] == ["plan-run"]
    assert not boards[0].top
    row, = page.plan_run.findChildren(Framed)
    assert not row.top and row.joined
    assert page.plan_run.layout().spacing() == 0
    assert row.sizeHint().height() == page.free.height()
