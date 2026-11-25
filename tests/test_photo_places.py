# OkeyDocu - tests/test_photo_places.py
# l10n: de
# A photo of the campaign laid at an element: by the service, on the tree and on the files.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import pytest
from PIL import Image
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QApplication, QMessageBox

from okeydocu.campaign.photo_marks import PhotoMark
from okeydocu.campaign.photo_view import PhotoView
from okeydocu.store import CampaignClosed
from okeydocu.ui.photo_shared import photo_mime_data
from okeydocu.ui.structure_tree import UNPLACED

from .photo_ui_helpers import make_campaign, photo_ids

LEFT, NONE = Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier
MOVE = Qt.DropAction.MoveAction


@pytest.fixture
def case(app, asset, tmp_path):
    campaign, _ = make_campaign(app, asset, tmp_path)
    return campaign, photo_ids(app, campaign)


def pictures(app, campaign, asset):
    return app.service.attachments(campaign, asset_id=asset)


def test_a_photo_laid_at_an_element_is_a_picture_there(app, asset, case):
    campaign, (first, second) = case
    name = app.db.one("SELECT original_name FROM photos WHERE id=?", first)["original_name"]
    app.service.photo_to_place(first, asset)
    (row,) = pictures(app, campaign, asset)
    assert (row["kind"], row["original_name"]) == ("image", name)
    assert app.service.attachment_path(campaign, row["file_name"]).is_file()
    assert photo_ids(app, campaign) == [second]


def test_the_file_of_the_photo_goes_with_it(app, asset, case):
    campaign, (first, _) = case
    row = app.db.one("SELECT * FROM photos WHERE id=?", first)
    path = app.service.photo_path(campaign, row["file_name"])
    app.service.photo_to_place(first, asset)
    assert not path.exists()


def test_the_picture_shows_what_the_photo_showed(app, asset, case):
    campaign, (first, _) = case
    view = PhotoView().turned(1).cut((0.0, 0.0, 1.0, 0.5))
    app.service.save_photo_notes(first, "", [], view)
    app.service.photo_to_place(first, asset)
    (row,) = pictures(app, campaign, asset)
    with Image.open(app.service.attachment_path(campaign, row["file_name"])) as image:
        assert image.size == (24, 16)  # 32 x 24 turned, then its upper half


def test_an_ended_campaign_keeps_its_photos(app, asset, case):
    campaign, (first, _) = case
    app.db.execute("UPDATE campaigns SET status='closed' WHERE id=?", campaign)
    with pytest.raises(CampaignClosed):
        app.service.photo_to_place(first, asset)


# On screen -------------------------------------------------------------------


@pytest.fixture
def page(window, app, asset, case):
    campaign, _ = case
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    return window.campaign


def drop_on(tree, item, photo_id) -> bool:
    """Enter, pass over and drop, as Qt delivers them during a drag."""
    mime = photo_mime_data(photo_id)
    where = tree.visualItemRect(item).center()
    enter = QDragEnterEvent(where, MOVE, mime, LEFT, NONE)
    tree.dragEnterEvent(enter)
    over = QDragMoveEvent(where, MOVE, mime, LEFT, NONE)
    tree.dragMoveEvent(over)
    if not (enter.isAccepted() and over.isAccepted()):
        return False
    tree.dropEvent(QDropEvent(QPointF(where), MOVE, mime, LEFT, NONE))
    for _ in range(3):  # the photo is laid after the drop, the views follow after that
        QApplication.processEvents()
    return True


def test_a_photo_dropped_on_an_element_of_the_tree_lies_there(page, app, asset, case):
    campaign, (first, second) = case
    app.service.stack_photo(first)
    page._data_changed()
    assert drop_on(page.structure, page.structure.items[asset], first)
    assert len(pictures(app, campaign, asset)) == 1
    assert page.stack.count == 0
    assert page.place_files.list.count() == 1
    assert photo_ids(app, campaign) == [second]


def test_what_has_no_location_takes_no_photo(page, app, asset, case):
    campaign, (first, _) = case
    app.db.execute("UPDATE measurements SET asset_id=NULL WHERE campaign_id=?", campaign)
    page._data_changed()
    tree = page.structure
    loose = next(tree.topLevelItem(i) for i in range(tree.topLevelItemCount())
                 if tree.topLevelItem(i).data(0, 0x0100) == UNPLACED)
    assert not drop_on(tree, loose, first)
    assert pictures(app, campaign, asset) == []


def test_the_tree_of_an_ended_campaign_takes_no_photo(page, app, asset, case):
    campaign, (first, _) = case
    app.db.execute("UPDATE campaigns SET status='closed' WHERE id=?", campaign)
    page.show_campaign(campaign)
    assert not drop_on(page.structure, page.structure.items[asset], first)


def test_a_photo_with_marks_asks_before_it_loses_them(page, app, asset, case, monkeypatch):
    campaign, (first, _) = case
    app.service.save_photo_notes(first, "defect", [PhotoMark(1, 0.1, 0.1, 0.2, 0.2, "Riss")])
    asked = []

    def question(*args):
        asked.append(args[2])
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", question)
    assert drop_on(page.structure, page.structure.items[asset], first)
    assert "Markierungen" in asked[0]
    assert pictures(app, campaign, asset) == []
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)
    assert drop_on(page.structure, page.structure.items[asset], first)
    assert len(pictures(app, campaign, asset)) == 1


def test_a_photo_dropped_on_the_files_of_the_element_lies_there(page, app, asset, case):
    campaign, (first, _) = case
    app.service.stack_photo(first)
    page._data_changed()
    files = page.place_files
    mime = photo_mime_data(first)
    enter = QDragEnterEvent(files.rect().center(), MOVE, mime, LEFT, NONE)
    files.dragEnterEvent(enter)
    assert enter.isAccepted()
    files.dropEvent(QDropEvent(QPointF(files.rect().center()), MOVE, mime, LEFT, NONE))
    QApplication.processEvents()
    assert files.list.count() == 1
    assert page.stack.count == 0
