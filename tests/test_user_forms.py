# OkeyDocu - tests/test_user_forms.py
# The signature pad, the form for a person, and the list of people.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QImage
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox

from okeydocu.ui.signature_pad import SignaturePad
from okeydocu.ui.user_form import UserForm
from okeydocu.ui.users import UsersOverlay


# Signature pad ---------------------------------------------------------------


def write(qtbot, pad):
    qtbot.addWidget(pad)
    pad.resize(320, 120)
    pad.show()
    left = Qt.MouseButton.LeftButton
    QTest.mousePress(pad, left, pos=QPoint(40, 60))
    QTest.mouseMove(pad, QPoint(120, 40))
    QTest.mouseMove(pad, QPoint(200, 70))
    QTest.mouseRelease(pad, left, pos=QPoint(200, 70))


def test_an_empty_pad_gives_nothing(qtbot):
    pad = SignaturePad()
    qtbot.addWidget(pad)
    assert pad.empty
    assert pad.data() is None


def test_what_was_written_keeps_its_place_on_the_line(qtbot):
    pad = SignaturePad()
    write(qtbot, pad)
    image = QImage.fromData(pad.data())
    assert (image.width(), image.height()) == (1200, 300)
    assert image.text("baseline") == "0.75"


def test_aligning_drags_the_signature_and_the_report_puts_it_on_the_line(qtbot):
    from okeydocu.reporting.pdf_parts import SignatureBox, _signature_image

    pad = SignaturePad()
    write(qtbot, pad)
    pad.set_aligning(True)
    assert not pad.strokes and pad.picture is not None
    before = pad.place.topLeft()
    left = Qt.MouseButton.LeftButton
    QTest.mousePress(pad, left, pos=QPoint(100, 60))
    QTest.mouseMove(pad, QPoint(140, 70))
    QTest.mouseRelease(pad, left, pos=QPoint(140, 70))
    assert pad.place.x() > before.x() and pad.place.y() > before.y()
    box = _signature_image(pad.data(), 200)
    assert isinstance(box, SignatureBox)
    assert box.wrap(200, 100)[1] == pytest.approx(box.box_height * 0.75)


def test_writing_leaves_a_transparent_background(qtbot):
    pad = SignaturePad()
    write(qtbot, pad)
    image = QImage.fromData(pad.data())
    assert image.pixelColor(0, image.height() - 1).alpha() == 0


def test_a_stored_signature_survives_saving_unchanged(qtbot):
    source = QImage(200, 80, QImage.Format.Format_ARGB32)
    source.fill(Qt.GlobalColor.black)
    pad = SignaturePad()
    qtbot.addWidget(pad)
    assert pad.load(_png(source))
    assert QImage.fromData(pad.data()).width() == 200


def test_clearing_empties_the_pad(qtbot):
    pad = SignaturePad()
    write(qtbot, pad)
    pad.clear()
    assert pad.empty


def test_a_file_that_is_no_image_is_refused(qtbot):
    pad = SignaturePad()
    qtbot.addWidget(pad)
    assert not pad.load(b"kein Bild")


def _png(image):
    from PySide6.QtCore import QBuffer, QIODevice

    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


# The form --------------------------------------------------------------------


def test_a_name_is_required(qtbot, app):
    form = UserForm(app)
    qtbot.addWidget(form)
    assert not form.ok_button.isEnabled()
    form.name.setText("Anna")
    assert form.ok_button.isEnabled()
    assert form.hint.text() == ""


def test_saving_stores_all_fields(qtbot, app):
    form = UserForm(app)
    qtbot.addWidget(form)
    form.title_field.setText("Dr.")
    form.name.setText("Anna")
    form.accept()
    user = app.db.user(form.saved_id)
    assert (user["title"], user["name"]) == ("Dr.", "Anna")


def test_changing_keeps_the_same_entry(qtbot, app):
    user = app.db.add_user("Anna")
    form = UserForm(app, user=app.db.user(user))
    qtbot.addWidget(form)
    form.name.setText("Anna B.")
    form.accept()
    assert len(app.db.users()) == 1
    assert app.db.user(user)["name"] == "Anna B."


def test_the_password_of_a_certificate_is_not_kept(qtbot, app, monkeypatch, tmp_path):
    class Info:
        name = "Anna"
        valid_until = __import__("datetime").datetime(2030, 1, 1)

    seen = []
    monkeypatch.setattr(
        "okeydocu.ui.user_form.certificate_info",
        lambda path, phrase: seen.append(phrase) or Info,
    )
    form = UserForm(app)
    qtbot.addWidget(form)
    form.name.setText("Anna")
    form.certificate.setText(str(tmp_path / "a.p12"))
    form.passphrase.setText("geheim")
    form.check_button.click()
    form.accept()
    assert seen == ["geheim"]
    assert form.passphrase.text() == ""
    user = app.db.user(form.saved_id)
    assert "geheim" not in " ".join(str(value) for value in tuple(user))
    assert user["certificate_until"] == "2030-01-01"
    assert "01.01.2030" in form.certificate_state.text()


# The list --------------------------------------------------------------------


def test_list_tells_what_is_set_up(qtbot, app):
    app.db.add_user("Anna", signature=b"x")
    overlay = UsersOverlay(app)
    qtbot.addWidget(overlay)
    text = overlay.list.item(0).text()
    assert "Anna" in text
    assert "Unterschrift hinterlegt" in text
    assert "kein Zertifikat" in text


def test_removing_asks_first(qtbot, app):
    app.db.add_user("Anna")
    overlay = UsersOverlay(app)
    qtbot.addWidget(overlay)
    overlay.remove_button.click()  # the default answer in tests is no
    assert overlay.list.count() == 1


def test_removing_after_confirmation(qtbot, app, monkeypatch):
    app.db.add_user("Anna")
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    overlay = UsersOverlay(app)
    qtbot.addWidget(overlay)
    overlay.remove_button.click()
    assert overlay.list.count() == 0


def test_a_person_with_a_signature_opens_and_keeps_it(qtbot, app):
    source = QImage(200, 80, QImage.Format.Format_ARGB32)
    source.fill(Qt.GlobalColor.black)
    user = app.db.add_user("Anna", signature=_png(source))
    form = UserForm(app, user=app.db.user(user))
    qtbot.addWidget(form)
    assert form.clear_button.isEnabled() and not form.pad.empty
