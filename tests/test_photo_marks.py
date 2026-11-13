# OkeyDocu - tests/test_photo_marks.py
# Numbered marks on a photo with their texts, its role, and moving it to another measurement.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import json
from datetime import datetime

import pytest
from PIL import Image
from PySide6.QtCore import QRectF

from okeydocu.campaign.photo_marks import PhotoMark
from okeydocu.campaign.seal import content
from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.ui import photo_gallery
from okeydocu.ui.photo_gallery import PHOTO_ID
from okeydocu.ui.photo_preview import PhotoPreview


@pytest.fixture
def photo(window, app, tmp_path):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    value = ResultValue("riso", "RISO", Quantity.parse("2MΩ"), Verdict.PASSED, ">1MΩ", "")
    first, second = (app.service.add_measurement(campaign, "riso", [value],
                                                 datetime(2026, 5, 4, 9, minute), Verdict.PASSED)
                     for minute in (0, 5))
    picture = tmp_path / "schrank.jpg"
    Image.new("RGB", (1600, 1200), (90, 100, 110)).save(picture)
    app.service.add_photo(first, picture)
    photo_id = app.db.one("SELECT id FROM photos WHERE measurement_id=?", first)["id"]
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    return {"page": page, "campaign": campaign, "first": first, "second": second,
            "photo": photo_id, "path": picture}


def _preview(app, window, photo):
    return PhotoPreview("schrank.jpg", "", photo["path"], window, app, photo["photo"])


def test_marks_and_role_are_kept_only_on_taking_them_over(app, window, photo):
    preview = _preview(app, window, photo)
    assert preview.editable and preview.ok_button.text() == "Übernehmen"
    preview.canvas.drawn.emit(QRectF(0.1, 0.2, 0.3, 0.2))
    preview.canvas.drawn.emit(QRectF(0.6, 0.6, 0.1, 0.1))
    preview.rows[1].setPlainText("Isolierung angeschmort")
    next(b for b in preview.roles.buttons() if b.text() == "Mangel").setChecked(True)
    assert app.service.photo_marks(photo["photo"]) == []  # nothing stored before accepting
    preview.accept()
    marks = app.service.photo_marks(photo["photo"])
    assert [(m.number, m.text) for m in marks] == [(1, "Isolierung angeschmort"), (2, "")]
    assert marks[0].x == pytest.approx(0.1) and marks[0].h == pytest.approx(0.2)
    assert app.service.photo_role(photo["photo"]) == "defect"


def test_a_removed_mark_lets_the_others_close_up(app, window, photo):
    app.service.save_photo_notes(photo["photo"], "", [
        PhotoMark(1, 0.1, 0.1, 0.1, 0.1, "eins"), PhotoMark(2, 0.3, 0.3, 0.1, 0.1, "zwei")])
    preview = _preview(app, window, photo)
    preview._remove(1)
    assert [(m.number, m.text) for m in preview.marks()] == [(1, "zwei")]


def test_a_text_shows_its_region_also_when_marks_are_hidden(app, window, photo):
    app.service.save_photo_notes(photo["photo"], "hint", [
        PhotoMark(1, 0.1, 0.1, 0.1, 0.1, "eins"), PhotoMark(2, 0.3, 0.3, 0.1, 0.1, "zwei")])
    preview = _preview(app, window, photo)
    preview.show_all.setChecked(False)
    preview._choose(2)
    assert [m.number for m in preview.canvas._shown()] == [2]


def test_a_closed_campaign_shows_its_marks_and_changes_nothing(app, window, photo):
    app.service.save_photo_notes(photo["photo"], "hint", [PhotoMark(1, 0.1, 0.1, 0.2, 0.2, "x")])
    app.service.close(photo["campaign"])
    preview = _preview(app, window, photo)
    assert not preview.editable and preview.ok_button.text() == "Zurück"
    assert preview.cancel_button.isHidden() and preview.rows[1].isReadOnly()


def test_the_seal_takes_marks_and_role_only_where_there_are_some(app, photo):
    plain = json.loads(content(app.db, photo["campaign"], "2026-05-04T12:00:00"))
    assert "role" not in plain["photos"][0] and "marks" not in plain["photos"][0]
    app.service.save_photo_notes(photo["photo"], "defect", [PhotoMark(1, 0.1, 0.1, 0.2, 0.2, "x")])
    noted = json.loads(content(app.db, photo["campaign"], "2026-05-04T12:00:00"))
    assert noted["photos"][0]["role"] == "defect"
    assert noted["photos"][0]["marks"][0]["text"] == "x"


def test_a_photo_dragged_from_the_gallery_moves_to_the_measurement_it_is_dropped_on(
        app, photo, monkeypatch):
    page = photo["page"]
    values = page.values
    row_first = next(r for r in range(values.table.rowCount())
                     if values.table.item(r, 0).data(0x0100) == photo["first"])
    values.table.selectRow(row_first)
    item = values.gallery.item(0)
    assert item.data(PHOTO_ID) == photo["photo"]
    carried = []
    monkeypatch.setattr(photo_gallery, "start_photo_drag",
                        lambda source, photo_id, pixmap=None: carried.append(photo_id))
    values.gallery.setCurrentItem(item)
    values.gallery.startDrag(None)
    assert carried == [photo["photo"]]
    row_second = next(r for r in range(values.table.rowCount())
                      if values.table.item(r, 0).data(0x0100) == photo["second"])
    target = values.table.visualItemRect(values.table.item(row_second, 0)).center()
    assert page._row_takes_photo(target)
    page._photo_dropped(photo["photo"], target)
    assert app.db.one("SELECT measurement_id FROM photos WHERE id=?", photo["photo"])[0] == \
        photo["second"]
    assert app.service.photos_of(photo["first"]) == []


def _click(view, point, double=False):
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    kind = QMouseEvent.Type.MouseButtonDblClick if double else QMouseEvent.Type.MouseButtonPress
    event = QMouseEvent(kind, QPointF(point), QPointF(view.mapToGlobal(point)),
                        Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton,
                        Qt.KeyboardModifier.NoModifier)
    (view.mouseDoubleClickEvent if double else view.mousePressEvent)(event)


def test_the_cross_on_a_gallery_photo_unpins_it_into_the_stack(app, photo, qtbot):
    page = photo["page"]
    values = page.values
    row_first = next(r for r in range(values.table.rowCount())
                     if values.table.item(r, 0).data(0x0100) == photo["first"])
    values.table.selectRow(row_first)
    gallery = values.gallery
    assert gallery.removable and gallery.count() == 1
    cross = gallery.cross_rect(gallery.model().index(0, 0))
    assert gallery.visualRect(gallery.model().index(0, 0)).contains(cross)
    _click(gallery, cross.center(), double=True)  # a double click there opens nothing
    _click(gallery, cross.center())
    assert app.service.photos_of(photo["first"]) == []
    assert [p["id"] for p in app.service.stacked_photos(photo["campaign"])] == [photo["photo"]]
    assert app.db.one("SELECT COUNT(*) FROM photos")[0] == 1  # the file stays
    assert page.stack.count == 1 and gallery.count() == 0


def test_a_closed_campaign_shows_no_cross(app, photo):
    app.service.close(photo["campaign"])
    page = photo["page"]
    page.show_campaign(photo["campaign"])
    values = page.values
    values.table.selectRow(next(r for r in range(values.table.rowCount())
                                if values.table.item(r, 0).data(0x0100) == photo["first"]))
    gallery = values.gallery
    assert gallery.count() == 1 and not gallery.removable
    assert not gallery.cross_at(gallery.cross_rect(gallery.model().index(0, 0)).center()).isValid()
