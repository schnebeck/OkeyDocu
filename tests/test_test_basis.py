# OkeyDocu - tests/test_test_basis.py
# What an element is tested to, inherited from the element above, and features with choices.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtWidgets import QComboBox

from okeydocu.reporting.context import build_context
from okeydocu.reporting.nodes import Letterhead
from okeydocu.reporting.template import default_template_text, parse_template, resolve
from okeydocu.store.kinds import Feature
from okeydocu.ui.element_form import ElementForm
from okeydocu.ui.kind_features import FeatureTable


@pytest.fixture
def tree(app):
    db = app.db
    customer = db.add_customer("Muster AG")
    root = db.add_asset(customer, "machine", "Presse")
    board = db.add_asset(customer, "distribution_board", "Schrank", parent_id=root)
    circuit = db.add_asset(customer, "circuit", "F1", parent_id=board)
    return root, board, circuit


def set_basis(app, asset_id, basis):
    row = app.db.asset(asset_id)
    app.db.update_asset(asset_id, row["kind"], row["name"], row["identifier"], row["manufacturer"],
                        row["type"], row["serial_no"], row["comment"], basis)


def test_an_element_follows_the_basis_above_until_it_has_its_own(app, tree):
    root, board, circuit = tree
    assert app.db.test_basis(circuit) == ("", "")
    set_basis(app, root, "DIN VDE 0100-600")
    assert app.db.test_basis(circuit) == ("", "DIN VDE 0100-600")
    set_basis(app, board, "DIN EN 60204-1")
    assert app.db.test_basis(circuit) == ("", "DIN EN 60204-1")
    assert app.db.test_basis(board) == ("DIN EN 60204-1", "DIN EN 60204-1")


def test_the_form_shows_what_is_followed_and_asks_the_top_for_one(qtbot, app, tree):
    root, board, _ = tree
    form = ElementForm(app)
    qtbot.addWidget(form)
    form.load(root)
    assert not form.basis_hint.isHidden()
    form.fields["basis"].setText("DIN VDE 0100-600")
    form.save()
    assert form.basis_hint.isHidden() and app.db.asset(root)["basis"] == "DIN VDE 0100-600"
    form.load(board)
    assert form.fields["basis"].placeholderText() == "wie darüber: DIN VDE 0100-600"


def test_a_feature_with_choices_offers_them_and_takes_another_value(qtbot, app, tree):
    circuit = tree[2]
    form = ElementForm(app)
    qtbot.addWidget(form)
    form.load(circuit)
    box = form.feature_fields["cross_section"]
    assert isinstance(box, QComboBox) and box.findText("1,5") >= 0
    box.setCurrentText("1,5")
    form.feature_fields["characteristic"].setCurrentText("C")
    form.feature_fields["cable_length"].setText("12")
    form.save()
    stored = app.db.asset_features(circuit)
    assert stored["cross_section"] == "1.5" and stored["characteristic"] == "C"
    assert stored["cable_length"] == "12"


def test_a_choice_can_always_be_emptied_or_replaced_by_own_text(qtbot):
    from okeydocu.ui.choice_box import EMPTY, OWN, ChoiceBox

    box = ChoiceBox(("B", "C"), "C")
    qtbot.addWidget(box)
    box.activated.emit(box.findData(EMPTY))
    assert box.currentText() == ""
    box.setCurrentIndex(box.findText("B"))
    box.activated.emit(box.findData(OWN))
    assert box.currentText() == ""
    box.lineEdit().setText("Bx")
    box.lineEdit().editingFinished.emit()
    assert box.currentText() == "Bx" and box.findText("Bx") < 0


def test_the_kind_editor_picks_the_list_a_feature_offers(qtbot, app):
    table = FeatureTable()
    qtbot.addWidget(table)
    lists = app.db.choice_lists()
    table.show_features((Feature("charakter", "Charakteristik", "", "characteristic"),), lists)
    assert table.table.item(0, 2).text() == "Charakteristik"
    delegate = table.table.itemDelegateForColumn(2)
    index = table.table.model().index(0, 2)
    editor = delegate.createEditor(table.table, None, index)
    editor.setCurrentIndex(editor.findData("rcd_type"))
    delegate.setModelData(editor, table.table.model(), index)
    assert table.features()[0].choice_list == "rcd_type"
    editor.setCurrentIndex(0)
    delegate.setModelData(editor, table.table.model(), index)
    assert table.features()[0].choice_list is None


def test_the_report_names_its_basis_in_the_title(app, tree):
    root = tree[0]
    set_basis(app, root, "DIN VDE 0100-600")
    campaign = app.service.create(root, "Prüfung", "Prüfer")
    nodes = resolve(parse_template(default_template_text()), build_context(app.service, campaign))
    head = next(node for node in nodes if isinstance(node, Letterhead))
    assert head.title == "Prüfprotokoll nach DIN VDE 0100-600"
