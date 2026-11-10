# EasyMeasurement - tests/test_window_photos.py
# The photo timeline and stack in the main window, tied to the measurement table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

from PIL import Image


def photo_campaign(window, app, asset, tmp_path):
    campaign = app.service.create(asset, "T", "P")
    moment = datetime(2026, 3, 1, 10, 0)
    measurement = app.service.add_measurement(campaign, "rlo", [], moment)
    path = tmp_path / "20260301_100030.jpg"
    Image.new("RGB", (8, 8), "red").save(path)
    app.service.import_photos(campaign, [path])
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    return campaign, measurement


def test_no_photos_no_timeline(window, app, asset):
    campaign = app.service.create(asset, "T", "P")
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    assert not window.campaign.timeline.isVisible()
    assert window.campaign.photo_tabs.tabText(1) == "Nicht zugeordnet"


def test_the_timeline_waits_to_be_asked_for_once_there_are_photos(window, app, asset, tmp_path):
    photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    assert page.header.assign_button.isVisible() and not page.timeline.isVisible()
    page.header.assign_button.click()
    assert page.timeline.isVisible() and page.timeline_action.isChecked()


def test_the_timeline_closes_by_its_own_button(window, app, asset, tmp_path):
    photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    page.timeline_action.setChecked(True)
    page.timeline.close_button.click()
    assert not page.timeline.isVisible() and not page.header.assign_button.isChecked()


def test_importing_photos_opens_the_timeline(window, app, asset, tmp_path, monkeypatch):
    from easymeasurement.ui import campaign_actions
    campaign = app.service.create(asset, "T", "P")
    app.service.add_measurement(campaign, "rlo", [], datetime(2026, 3, 1, 10, 0))
    path = tmp_path / "20260301_100030.jpg"
    Image.new("RGB", (8, 8), "red").save(path)
    monkeypatch.setattr(campaign_actions, "pick_images", lambda parent: [path])
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    page.import_photos()
    assert page.timeline.isVisible()


def test_the_scroll_bar_follows_zoom_and_moves_the_view(window, app, asset, tmp_path):
    photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    page.timeline_action.setChecked(True)
    view, scroll = page.timeline.view, page.timeline.scroll
    view.fit()
    assert not scroll.isEnabled()  # everything in view
    view.axis.zoom_at(view.axis.left, 8.0)
    view.relayout()
    assert scroll.isEnabled()
    scroll.setValue(0)  # the first thing on the tracks at the left edge
    first = view.axis.seconds_at(view.axis.left)
    assert first < view.data.content_range()[0] and not view.fitted
    scroll.setValue(scroll.maximum())
    assert view.axis.seconds_at(view.axis.left) > first


def test_photo_taken_off_shows_up_on_the_stack_and_in_the_table(window, app, asset, tmp_path):
    campaign, _ = photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    page.timeline._write(app.service.stack_photo, app.service.photos(campaign)[0]["id"])
    assert page.photo_tabs.tabText(1) == "Nicht zugeordnet (1)"
    assert page.stack.count == 1
    assert page.values.table.item(0, 7).text() == ""


def test_a_mark_on_the_timeline_selects_the_row(window, app, asset, tmp_path):
    _, measurement = photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    page.timeline.measurement_chosen.emit(measurement)
    assert page.values.table.currentRow() == 0


def test_a_dropped_photo_is_pinned_to_the_row(window, app, asset, tmp_path):
    campaign, measurement = photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    photo = app.service.photos(campaign)[0]["id"]
    app.service.stack_photo(photo)
    position = page.values.table.visualItemRect(page.values.table.item(0, 0)).center()
    assert page._row_takes_photo(position)
    page._photo_dropped(photo, position)
    row = app.service.photos(campaign)[0]
    assert (row["placement"], row["measurement_id"]) == ("pinned", measurement)
    assert page.stack.count == 0


def test_a_closed_campaign_takes_no_dropped_photo(window, app, asset, tmp_path):
    campaign, _ = photo_campaign(window, app, asset, tmp_path)
    app.service.close(campaign)
    page = window.campaign
    page.refresh()
    position = page.values.table.visualItemRect(page.values.table.item(0, 0)).center()
    assert not page._row_takes_photo(position)


def test_loose_photos_stand_out_in_the_side_panel_and_the_checks_line(window, app, asset,
                                                                      tmp_path):
    campaign, _ = photo_campaign(window, app, asset, tmp_path)
    page = window.campaign
    assert "nicht zugeordnet" not in page.header.checks.text()
    page.timeline._write(app.service.stack_photo, app.service.photos(campaign)[0]["id"])
    assert "#d35400" in page.photo_section.toggle.styleSheet()
    assert page.photo_tabs.tabBar().tabTextColor(1).name() == "#d35400"
    assert "1 Foto nicht zugeordnet" in page.header.checks.text()
    window.side_action.setChecked(False)
    page.photo_section.toggle.setChecked(False)
    page.photo_tabs.setCurrentIndex(0)
    page._follow_check("stack")
    assert window.side_action.isChecked() and page.photo_section.expanded
    assert page.photo_tabs.currentIndex() == 1


def test_the_confirmation_says_loose_photos_miss_the_report(window, app, asset, tmp_path):
    from easymeasurement.ui.confirm_overlay import ConfirmOverlay
    campaign, _ = photo_campaign(window, app, asset, tmp_path)
    app.service.stack_photo(app.service.photos(campaign)[0]["id"])
    overlay = ConfirmOverlay(app, app.service.campaign(campaign), window)
    assert "1 Foto ist keiner Messung zugeordnet" in overlay.summary.text()
