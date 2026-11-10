# EasyMeasurement - tests/test_user_overlay.py
# Overlays over the window, and changing the person of a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QPoint, Qt, QTimer
from PySide6.QtTest import QTest

from easymeasurement.ui.overlay import Overlay


def run_overlay(overlay, action):
    QTimer.singleShot(0, action)
    return overlay.exec()


def test_overlay_lies_over_the_whole_window_and_blocks_it(window):
    overlay = Overlay("Test", window.campaign)
    seen = {}

    def look():
        seen["size"] = overlay.size()
        seen["menu"] = window.menuBar().isEnabled()
        seen["work"] = window.campaign.isEnabled()
        overlay.reject()

    assert run_overlay(overlay, look) == 0
    assert seen["size"] == window.size()
    assert not seen["menu"]
    assert not seen["work"]
    assert window.menuBar().isEnabled()
    assert window.campaign.isEnabled()


@pytest.mark.parametrize("key, result", [(Qt.Key.Key_Escape, 0), (Qt.Key.Key_Return, 1)])
def test_escape_leaves_and_enter_confirms(window, key, result):
    overlay = Overlay("Test", window.campaign)
    assert run_overlay(overlay, lambda: QTest.keyClick(overlay, key)) == result


def test_inputs_can_follow_each_other(window):
    first = Overlay("Eins", window.campaign)
    run_overlay(first, first.reject)
    second = Overlay("Zwei", window.campaign)
    assert run_overlay(second, second.accept) == 1
    assert window.campaign.isEnabled()


def test_an_input_can_open_another_one_on_top(window):
    outer = Overlay("Außen", window.campaign)
    seen = {}

    def nested():
        inner = Overlay("Innen", outer)
        run_overlay(inner, inner.accept)
        seen["outer enabled again"] = outer.isEnabled()
        outer.accept()

    assert run_overlay(outer, nested) == 1
    assert seen["outer enabled again"]


def test_enter_does_nothing_while_something_is_missing(window):
    overlay = Overlay("Test", window.campaign)
    overlay.ok_button.setEnabled(False)

    def press():
        QTest.keyClick(overlay, Qt.Key.Key_Return)
        assert overlay._loop.isRunning()
        overlay.reject()

    assert run_overlay(overlay, press) == 0


def test_a_click_beside_the_card_leaves_the_input_open(window):
    overlay = Overlay("Test", window.campaign)

    def click():
        QTest.mouseClick(overlay, Qt.MouseButton.LeftButton, pos=QPoint(2, 2))
        assert overlay._loop.isRunning()
        overlay.reject()

    assert run_overlay(overlay, click) == 0


def test_closing_the_window_ends_an_open_overlay(window):
    overlay = Overlay("Test", window.campaign)
    assert run_overlay(overlay, window.close) == 0


def test_card_follows_the_window(window):
    overlay = Overlay("Test", window.campaign)
    seen = {}

    def resize():
        window.resize(1000, 600)
        seen["centre"] = overlay.card.geometry().center().x()
        overlay.reject()

    run_overlay(overlay, resize)
    assert abs(seen["centre"] - 500) <= 2


def test_a_reading_still_arrives_behind_an_overlay(window, app, asset):
    campaign = app.service.create(asset, "T", "Anna", driver_key="simulator")
    window.campaign.refresh()
    window.campaign.enter(campaign)
    meter = app.devices.driver(app.service.campaign(campaign))
    overlay = Overlay("Test", window.campaign)

    def measure():
        meter.simulate_measurement("u")
        overlay.reject()

    run_overlay(overlay, measure)
    assert len(app.service.measurements(campaign)) == 1


def test_person_is_changed_from_the_header(window, app, asset, monkeypatch):
    first, second = app.db.add_user("Anna"), app.db.add_user("Berta")
    campaign = app.service.create(asset, "T", "Anna", user_id=first)
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)

    def choose(overlay):
        overlay.tester.fill(second)
        return 1

    monkeypatch.setattr("easymeasurement.ui.campaign_views.TesterOverlay.exec", choose)
    window.campaign.header.details.linkActivated.emit("tester")
    assert app.service.campaign(campaign)["tester"] == "Berta"
    assert "Berta" in window.campaign.header.details.text()


def test_closed_campaign_offers_no_change_of_person(window, app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    app.service.close(campaign)
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    assert "href" not in window.campaign.header.details.text()
    assert not window.campaign.tester_action.isEnabled()


def test_signing_starts_with_the_certificate_of_the_person(window, app, asset, monkeypatch):
    from easymeasurement.ui import report_signing

    user = app.db.add_user("Anna", certificate_path="/tmp/anna.p12")
    campaign = app.service.create(asset, "T", "Anna", user_id=user)
    app.service.close(campaign)
    seen = []
    monkeypatch.setattr(report_signing.SignOverlay, "exec", lambda self: seen.append(self.certificate.path.text()) or 0)
    report_signing.sign_report(window, app, {"campaign_id": campaign})
    assert seen == ["/tmp/anna.p12"]
