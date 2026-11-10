# EasyMeasurement - tests/test_guided_instrument.py
# Wiring and the instrument's clock in the guided flow, with the simulator.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime, timedelta

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QColor, QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from easymeasurement.campaign.service import ClockState
from easymeasurement.ui.status_badges import clock_icon

from . import guided_helpers
from .guided_helpers import click_wire

# pytest looks fixtures up by name in the test module.
page, window = guided_helpers.page, guided_helpers.window


def test_setup_cannot_be_confirmed_before_it_is_connected(page):
    assert not page.confirm_button.isEnabled()
    page.device_set.setChecked(True)
    assert not page.confirm_button.isEnabled()
    for index in range(page.wiring.total):
        click_wire(page.wiring, index)
    assert page.confirm_button.isEnabled()


def test_setting_check_is_required_too(page):
    for index in range(page.wiring.total):
        click_wire(page.wiring, index)
    assert not page.confirm_button.isEnabled()


def test_connections_are_ticked_in_order_only(page):
    click_wire(page.wiring, 1)
    assert page.wiring.done == 0
    click_wire(page.wiring, 0)
    click_wire(page.wiring, 1)
    assert page.wiring.done == 2


def test_last_connection_can_be_taken_back(page):
    click_wire(page.wiring, 0)
    click_wire(page.wiring, 0)
    assert page.wiring.done == 0


def test_crossing_wires_can_both_be_ticked(page):
    page.steps.setCurrentRow(2)
    view = page.wiring
    for index in range(view.total):
        click_wire(view, index)
    assert view.complete


def test_a_click_exactly_on_a_crossing_reaches_the_next_wire(page):
    page.steps.setCurrentRow(2)
    view = page.wiring
    click_wire(view, 0)
    crossing = view.wires[1].path().pointAtPercent(0.5)
    point = view.mapFromScene(crossing)
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(point.x(), point.y()))
    assert view.done == 2


def test_markers_do_not_overlap(page):
    page.steps.setCurrentRow(2)
    view = page.wiring
    points = [view.wire_point(i) for i in range(view.total)]
    for a in range(len(points)):
        for b in range(a + 1, len(points)):
            distance = (points[a] - points[b]).manhattanLength()
            assert distance > 30


def test_marker_and_its_label_sit_together(page):
    page.steps.setCurrentRow(2)
    view = page.wiring
    for index, (badge, label) in enumerate(view.badges):
        point = view.wire_point(index)
        assert badge.rect().center() == point
        centre = label.mapToScene(label.boundingRect().center())
        assert (centre - point).manhattanLength() < 3


def test_cross_wired_step_draws_what_the_manual_says(page):
    page.steps.setCurrentRow(2)
    wires = {w.target: w.socket for w in page.wiring.step.wiring.wires}
    assert wires == {"l1": "1(L)", "l2": "3(PE)", "l3": "2(N)"}


def _skew_clock(page, seconds):
    campaign = page._campaign()
    meter = page.app.devices.driver(campaign)
    meter._skew = timedelta(seconds=seconds)
    return meter


def test_clock_check_offers_to_set_a_clock_that_is_off(page, monkeypatch):
    meter = _skew_clock(page, 3600)
    questions = []

    def yes(*args):
        questions.append(args[2])
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", yes)
    page.window().campaign.check_clock()
    assert "+3600 s" in questions[0] or "+3599 s" in questions[0]
    assert abs(meter.read_clock() - datetime.now()) < timedelta(seconds=2)
    assert abs(page._campaign()["clock_offset_s"]) < 2


def test_clock_check_leaves_the_clock_alone_when_declined(page):
    meter = _skew_clock(page, 3600)
    page.window().campaign.check_clock()
    assert meter.read_clock() - datetime.now() > timedelta(seconds=3590)
    assert page._campaign()["clock_offset_s"] > 3590


def test_offset_can_be_stated_by_hand(page, monkeypatch):
    monkeypatch.setattr(QInputDialog, "getInt", lambda *_: (-648, True))
    page.window().campaign.correct_clock()
    assert page._campaign()["clock_offset_s"] == -648


def test_badge_shows_the_synchronised_clock(page):
    assert page.window().campaign.clock.state is ClockState.SYNCED
    assert page.window().campaign.clock.isVisible()
    assert "synchron" in page.window().campaign.clock.text.text()
    assert not page.window().campaign.clock.icon.pixmap().isNull()


def test_badge_changes_when_a_check_finds_a_deviation(page):
    _skew_clock(page, 120)
    page.window().campaign.check_clock()
    assert page.window().campaign.clock.state is ClockState.OFFSET


def test_badge_returns_after_the_clock_was_set(page, monkeypatch):
    _skew_clock(page, 120)
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    page.window().campaign.check_clock()
    assert page.window().campaign.clock.state is ClockState.SYNCED


def test_three_states_look_different_without_colour():
    face = QColor("black")
    images = [clock_icon(state, face).toImage().convertToFormat(QImage.Format.Format_Grayscale8)
              for state in ClockState]
    assert images[0] != images[1] != images[2] != images[0]
