# OkeyDocu - tests/test_pending_marks.py
# Fields changed but not yet applied stand out until they are applied; list words read and
# store the same in every language.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from PySide6.QtWidgets import QCheckBox, QComboBox, QLineEdit, QPlainTextEdit, QVBoxLayout, QWidget

from okeydocu.l10n import speaking
from okeydocu.ui.choice_box import ChoiceBox, field_text
from okeydocu.ui.element_form import ElementOverlay
from okeydocu.ui.pending_marks import PendingMarks


def form(qtbot):
    root = QWidget()
    qtbot.addWidget(root)
    line, box, text, check = QLineEdit("alt"), QComboBox(), QPlainTextEdit("Notiz"), QCheckBox()
    box.addItems(["A", "B"])
    layout = QVBoxLayout(root)
    for widget in (line, box, text, check):
        layout.addWidget(widget)
    marks = PendingMarks(root)
    marks.watch()
    return marks, line, box, text, check


def test_a_changed_field_is_pending_until_its_value_returns(qtbot):
    marks, line, box, text, check = form(qtbot)
    assert marks.pending() == []
    line.setText("neu")
    box.setCurrentIndex(1)
    text.setPlainText("Notiz!")
    check.setChecked(True)
    assert set(marks.pending()) == {line, box, text, check}
    line.setText("alt")
    assert line not in marks.pending()


def test_applying_takes_the_fields_as_they_are(qtbot):
    marks, line, *_ = form(qtbot)
    line.setText("neu")
    marks.watch()
    assert marks.pending() == []
    line.setText("noch neuer")
    assert marks.pending() == [line]


def test_a_read_only_field_is_not_watched(qtbot):
    marks, line, *_ = form(qtbot)
    line.setReadOnly(True)
    marks.watch()
    assert line not in marks.start


def test_every_card_marks_what_is_not_yet_applied(window, app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    overlay = ElementOverlay(app, machine, window)
    overlay._open()
    name = overlay.form.fields["name"]
    name.setText("Presse 2")
    assert overlay.pending_marks.pending() == [name]
    overlay.reject()


def test_a_list_word_reads_in_the_language_and_stores_as_the_list_holds_it(app):
    lists = app.db.choice_lists()
    with speaking("de"):
        box = ChoiceBox(lists["n_terminal"], "left")
        assert box.currentText() == "links"
        assert field_text(box) == "left"
        box.setEditText("rechts")
        assert field_text(box) == "right"
        box.setEditText("eigener Text")
        assert field_text(box) == "eigener Text"
