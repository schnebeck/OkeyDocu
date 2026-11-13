# OkeyDocu - tests/test_photo_view.py
# Turning a photo and cutting it to a part, without touching the original.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import hashlib
from datetime import datetime

import pytest
from PIL import Image
from PySide6.QtCore import QRectF

from okeydocu.campaign.photo_marks import PhotoMark
from okeydocu.campaign.photo_view import PhotoView, move_mark
from okeydocu.campaign.seal import content
from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.reporting.pdf_parts import _photo
from okeydocu.ui.photo_preview import PhotoPreview
from okeydocu.ui.photo_shared import read_thumbnail


def test_a_quarter_turn_moves_the_top_to_the_right():
    view = PhotoView().turned(1)
    assert view.into(0, 0) == (1, 0) and view.out_of(1, 0) == (0, 0)
    assert view.turned(-1) == PhotoView() and view.turned(3) == PhotoView()


def test_a_cut_part_turns_along_with_the_photo():
    top_half = PhotoView().turned(1).cut((0.5, 0.0, 0.5, 1.0))
    assert top_half.turned(1) == PhotoView(180, (0.0, 0.5, 1.0, 0.5))
    assert top_half.whole() == PhotoView(90)


def test_a_mark_stays_on_its_spot_and_goes_once_it_is_cut_away():
    mark = PhotoMark(1, 0.1, 0.2, 0.3, 0.1, "Klemme")
    turned = move_mark(mark, PhotoView(), PhotoView(90))
    assert (turned.x, turned.y, turned.w, turned.h) == pytest.approx((0.7, 0.1, 0.1, 0.3))
    back = move_mark(turned, PhotoView(90), PhotoView())
    assert (back.x, back.y, back.w, back.h) == pytest.approx((0.1, 0.2, 0.3, 0.1))
    assert move_mark(mark, PhotoView(), PhotoView(0, (0.5, 0.5, 0.5, 0.5))) is None


def test_the_view_is_stored_as_written():
    view = PhotoView(270, (0.25, 0.0, 0.5, 1.0))
    assert PhotoView.stored(270, view.crop_text()) == view
    assert PhotoView.stored(0, "") == PhotoView() and PhotoView().crop_text() == ""


def picture(path, size=(1600, 1200)):
    Image.new("RGB", size, (90, 100, 110)).save(path)
    return path


def test_the_report_shows_the_photo_turned_and_cut(tmp_path):
    path = picture(tmp_path / "a.jpg")
    turned = _photo(path, 100, (), PhotoView(90))
    assert turned.drawHeight == pytest.approx(100 * 1600 / 1200)
    cut = _photo(path, 100, (), PhotoView(0, (0.0, 0.0, 0.5, 1.0)))
    assert cut.drawHeight == pytest.approx(100 * 1200 / 800)


def test_a_thumbnail_follows_the_view(qtbot, tmp_path):
    path = picture(tmp_path / "b.jpg")
    assert read_thumbnail(str(path), PhotoView(90)).height() > read_thumbnail(str(path)).height()


@pytest.fixture
def photo(window, app, tmp_path):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    value = ResultValue("riso", "RISO", Quantity.parse("2MΩ"), Verdict.PASSED, ">1MΩ", "")
    measurement = app.service.add_measurement(campaign, "riso", [value],
                                              datetime(2026, 5, 4, 9), Verdict.PASSED)
    path = picture(tmp_path / "schrank.jpg")
    app.service.add_photo(measurement, path)
    row = app.db.one("SELECT id, file_name FROM photos WHERE measurement_id=?", measurement)
    stored = app.service.photo_path(campaign, row["file_name"])
    return {"campaign": campaign, "photo": row["id"], "path": stored}


def test_turning_and_cutting_in_the_large_view_keep_the_original(app, window, photo):
    before = hashlib.sha256(photo["path"].read_bytes()).hexdigest()
    preview = PhotoPreview("schrank.jpg", "", photo["path"], window, app, photo["photo"])
    preview.canvas.drawn.emit(QRectF(0.1, 0.1, 0.2, 0.2))
    wide = preview.canvas.pixmap.size()
    preview.turn_right.click()
    assert preview.canvas.pixmap.width() < wide.width()
    preview.cut_button.setChecked(True)
    preview.canvas.drawn.emit(QRectF(0.0, 0.0, 1.0, 0.5))
    assert not preview.cut_button.isChecked() and preview.whole_button.isEnabled()
    preview.accept()
    view = app.service.photo_view(photo["photo"])
    assert view.rotation == 90 and view.crop == pytest.approx((0.0, 0.0, 1.0, 0.5))
    (mark,) = app.service.photo_marks(photo["photo"])
    assert (mark.x, mark.y) == pytest.approx((0.7, 0.2))
    assert app.service.view_of_file(photo["path"]) == view
    assert hashlib.sha256(photo["path"].read_bytes()).hexdigest() == before


def test_the_seal_takes_the_view_only_where_there_is_one(app, photo):
    plain = content(app.db, photo["campaign"], "2026-05-04T10:00:00").decode()
    assert "rotation" not in plain and "crop" not in plain
    app.service.save_photo_notes(photo["photo"], "", [], PhotoView(180))
    assert '"rotation": 180' in content(app.db, photo["campaign"], "2026-05-04T10:00:00").decode()
