# OkeyDocu - tests/test_photo_pin_ui.py
# Dragging a photo up onto a measurement takes only this photo there.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PySide6.QtCore import QPoint

from okeydocu.ui import photo_timeline_mouse

from .photo_ui_helpers import (
    centre_of,
    drag,
    make_campaign,
    mark_point,
    move,
    open_timeline,
    owners,
    photo_ids,
    press,
    release,
    stored_shift,
)


@pytest.fixture
def case(app, asset, tmp_path):
    return make_campaign(app, asset, tmp_path)


@pytest.fixture
def timeline(qtbot, app, case):
    return open_timeline(qtbot, app, case[0])


def test_up_onto_a_measurement_pins_only_this_photo(qtbot, app, timeline, case):
    view = timeline.view
    first, second = photo_ids(app, case[0])
    with qtbot.waitSignal(timeline.changed):
        drag(view, centre_of(view, first), mark_point(view, case[1][2]))
    rows = app.service.photos(case[0])
    assert (rows[0]["placement"], rows[0]["measurement_id"]) == ("pinned", case[1][2])
    assert rows[1]["placement"] == "timeline"
    assert stored_shift(app, case[0]) == 0


def test_the_hint_says_what_will_happen(app, timeline, case):
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    press(view, start)
    move(view, start + QPoint(50, 0))
    assert timeline.hint_label.text().startswith("Alle Fotos verschieben")
    move(view, mark_point(view, case[1][2]))
    assert "nur dieses Foto" in timeline.hint_label.text()
    assert "10:20:00" in timeline.hint_label.text()
    assert view.mark_items[case[1][2]].marked
    release(view, mark_point(view, case[1][2]))
    assert not view.mark_items[case[1][2]].marked


def test_the_others_go_back_while_one_is_lifted_up(app, timeline, case):
    view = timeline.view
    first, second = photo_ids(app, case[0])
    x = view.photo_items[second].pos().x()
    start = centre_of(view, first)
    press(view, start)
    move(view, start + QPoint(70, 0))
    assert view.photo_items[second].pos().x() != pytest.approx(x)
    move(view, mark_point(view, case[1][2]))
    assert view.photo_items[second].pos().x() == pytest.approx(x)
    release(view, mark_point(view, case[1][2]))


def test_changing_ones_mind_during_the_drag(app, timeline, case):
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    press(view, start)
    move(view, mark_point(view, case[1][2]))
    move(view, start + QPoint(40, 0))
    release(view, start + QPoint(40, 0))
    assert [row["placement"] for row in app.service.photos(case[0])] == ["timeline"] * 2
    assert stored_shift(app, case[0]) != 0


def test_a_pinned_photo_can_go_to_another_measurement(app, qtbot, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path)
    photo = photo_ids(app, campaign)[0]
    app.service.pin_photo(photo, measured[0])
    view = open_timeline(qtbot, app, campaign).view
    drag(view, centre_of(view, photo), mark_point(view, measured[2]))
    assert owners(app, campaign)[0] == measured[2]


def test_a_pinned_photo_slid_sideways_stays(app, qtbot, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path)
    photo = photo_ids(app, campaign)[0]
    app.service.pin_photo(photo, measured[1])
    timeline = open_timeline(qtbot, app, campaign)
    view = timeline.view
    x = view.photo_items[photo].pos().x()
    start = centre_of(view, photo)
    press(view, start)
    move(view, start + QPoint(60, 0))
    assert "bleibt" in timeline.hint_label.text()
    release(view, start + QPoint(60, 0))
    assert view.photo_items[photo].pos().x() == pytest.approx(x)
    assert stored_shift(app, campaign) == 0


def test_leaving_the_view_hands_the_photo_to_a_real_drag(monkeypatch, app, timeline, case):
    carried = []
    monkeypatch.setattr(
        photo_timeline_mouse, "start_photo_drag", lambda _, photo, __: carried.append(photo)
    )
    view = timeline.view
    photo = photo_ids(app, case[0])[0]
    start = centre_of(view, photo)
    press(view, start)
    move(view, start + QPoint(50, 0))
    move(view, QPoint(start.x(), view.tracks.height + 40))
    assert carried == [photo]
    assert view.mouse.gesture is None
    assert stored_shift(app, case[0]) == 0
    assert view.data.shift == 0


def test_pinning_to_the_same_measurement_is_no_change(app, qtbot, asset, tmp_path):
    campaign, measured = make_campaign(app, asset, tmp_path)
    photo = photo_ids(app, campaign)[0]
    app.service.pin_photo(photo, measured[1])
    timeline = open_timeline(qtbot, app, campaign)
    view = timeline.view
    seen = []
    timeline.changed.connect(lambda: seen.append(1))
    drag(view, centre_of(view, photo), mark_point(view, measured[1]))
    assert seen == []


def test_a_campaign_closed_behind_the_timeline_is_said_and_locks(
    monkeypatch, app, timeline, case
):
    said = []
    monkeypatch.setattr("okeydocu.ui.photo_timeline.show_error",
                        lambda parent, text: said.append(text))
    seen = []
    timeline.changed.connect(lambda: seen.append(1))
    view = timeline.view
    start = centre_of(view, photo_ids(app, case[0])[0])
    app.service.close(case[0])
    drag(view, start, start + QPoint(80, 0))
    assert said and "abgeschlossen" in said[0]
    assert seen == []
    assert timeline.read_only
    assert stored_shift(app, case[0]) == 0
