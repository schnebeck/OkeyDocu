# OkeyDocu - tests/test_attachment_ui.py
# Notes and files on a measurement or a place, in the window and in the report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PIL import Image
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QDropEvent

from okeydocu.reporting.context import build_context as report_context
from okeydocu.reporting.nodes import Fields, Footnoted, Photos
from okeydocu.reporting.template import parse_template, default_template_text, resolve
from okeydocu.ui.attachment_list import NoteOverlay


@pytest.fixture
def pdf(tmp_path):
    path = tmp_path / "Schaltplan.pdf"
    path.write_bytes(b"%PDF-1.4 test")
    return path


@pytest.fixture
def image(tmp_path):
    path = tmp_path / "Typenschild.png"
    Image.new("RGB", (8, 8), "red").save(path, "PNG")
    return path


@pytest.fixture
def shown(window, app, asset):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    measurement = app.service.add_measurement(campaign, "rlo", [])
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    window.campaign.values.table.selectRow(0)
    return window.campaign, campaign, measurement


def drop(widget, paths):
    data = QMimeData()
    data.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    event = QDropEvent(QPointF(5, 5), Qt.DropAction.CopyAction, data,
                       Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    widget.dropEvent(event)


# On a measurement ------------------------------------------------------------


def test_a_pdf_dropped_on_the_measurement_is_attached(shown, app, pdf):
    page, campaign, measurement = shown
    drop(page.values.editor.attachments, [pdf])
    assert [r["original_name"] for r in app.service.attachments(campaign, measurement)] == [
        "Schaltplan.pdf"
    ]
    assert page.values.editor.attachments.list.count() == 1


def test_an_image_on_the_measurement_joins_its_photos(shown, app, image):
    page, _, measurement = shown
    page.values.editor.attachments.add_files([image])
    assert len(app.service.photos_of(measurement)) == 1
    assert page.values.gallery.count() == 1


def test_a_measurement_offers_files_but_no_second_remark(shown):
    files = shown[0].values.editor.attachments
    assert files.file_button.isVisible()
    assert not files.note_button.isVisible()


def test_an_unknown_file_is_explained(shown, app, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr("okeydocu.ui.attachment_list.show_error",
                        lambda _, text: errors.append(text))
    other = tmp_path / "liste.xlsx"
    other.write_bytes(b"x")
    shown[0].values.editor.attachments.add_files([other])
    assert "liste.xlsx" in errors[0]


def test_removing_an_attachment(shown, app, pdf):
    page, campaign, measurement = shown
    files = page.values.editor.attachments
    files.add_files([pdf])
    files.list.setCurrentRow(0)
    files.remove_button.click()
    assert app.service.attachments(campaign, measurement) == []


# On a place ------------------------------------------------------------------


def test_a_note_on_the_place(shown, app, asset, monkeypatch):
    page, campaign, _ = shown

    def write(overlay):
        overlay.text.setPlainText("Schrank verschlossen, Schlüssel beim Hausmeister")
        return 1

    monkeypatch.setattr(NoteOverlay, "exec", write)
    page.place_files.note_button.click()
    assert app.service.attachments(campaign, asset_id=asset)[0]["text"].startswith("Schrank")
    assert page.place_files.list.count() == 1


def test_a_closed_campaign_shows_attachments_but_offers_nothing(window, app, asset, pdf):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    app.service.add_attachment(campaign, pdf, asset_id=asset)
    app.service.close(campaign)
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    files = window.campaign.place_files
    assert files.list.count() == 1
    assert not files.file_button.isVisible()
    assert not files.note_button.isVisible()


def test_the_note_needs_text(qtbot):
    overlay = NoteOverlay("Halle")
    qtbot.addWidget(overlay)
    assert not overlay.ok_button.isEnabled()
    overlay.text.setPlainText("x")
    assert overlay.ok_button.isEnabled()


# In the report ---------------------------------------------------------------


def nodes(app, campaign):
    return resolve(parse_template(default_template_text()), report_context(app.service, campaign))


def test_notes_and_files_of_a_place_are_in_the_report(app, asset, pdf, image):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    app.service.add_comment(campaign, "Schrank verschlossen", asset_id=asset)
    app.service.add_attachment(campaign, pdf, asset_id=asset)
    app.service.add_attachment(campaign, image)
    found = nodes(app, campaign)
    rows = [row for node in found if isinstance(node, Fields) for row in node.rows]
    assert ("Halle", "Schrank verschlossen") in rows
    assert ("Halle", "Anhang Schaltplan.pdf") in rows
    photos = [item for node in found if isinstance(node, Photos) for item in node.items]
    assert photos[0][1] == "Prüfung allgemein"


def remarks(app, campaign) -> list[str]:
    tables = [node.body for node in nodes(app, campaign) if isinstance(node, Footnoted)]
    return [row[-1] for table in tables for row in table.rows]


def test_a_file_on_a_single_measurement_is_named(app, asset, pdf):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    measurement = app.service.add_measurement(campaign, "rlo", [])
    app.service.add_attachment(campaign, pdf, measurement_id=measurement)
    assert remarks(app, campaign) == ["Anhang Schaltplan.pdf"]


def test_a_remark_stands_in_the_row_of_its_measurement(app, asset):
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    app.service.add_measurement(campaign, "rlo", [])
    app.service.add_measurement(campaign, "rlo", [], comment="Klemme nachgezogen")
    assert remarks(app, campaign) == ["", "Klemme nachgezogen"]


def test_a_photo_of_the_measurement_opens_large(shown, image, monkeypatch):
    from okeydocu.ui.photo_overlays import PhotoPreview

    page = shown[0]
    page.values.editor.attachments.add_files([image])
    opened = []
    monkeypatch.setattr(PhotoPreview, "exec", lambda overlay: opened.append(overlay) or 0)
    page.values.gallery.itemActivated.emit(page.values.gallery.item(0))
    assert len(opened) == 1
