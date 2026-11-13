# OkeyDocu - tests/test_template_editor.py
# The graphical template editor in the real window.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtWidgets import QMessageBox

from okeydocu.reporting.nodes import Footnoted
from okeydocu.reporting.template import Paragraph, Table, parse_template, resolve
from okeydocu.reporting.template_model import BLOCK_LABELS, dump_template, new_block
from okeydocu.ui.template_document import sample_context



@pytest.fixture
def page(template_page):
    return template_page

def repeat_path(page):
    index = next(i for i, b in enumerate(page.template["blocks"]) if b["type"] == "steps")
    return (index,)


def stored(page):
    return parse_template(page.app.db.templates()[0]["body"])


def test_a_template_opens_as_blocks(page):
    assert page.tree.topLevelItemCount() > 5
    item = page.tree.topLevelItem(repeat_path(page)[0])
    assert item.childCount() == 3


@pytest.mark.parametrize("kind", BLOCK_LABELS)
def test_every_block_type_can_be_added_and_rendered(page, kind):
    page.tree.setCurrentItem(page.tree.topLevelItem(0))
    page.add_block(kind)
    assert page.preview()
    assert page.message.text() == ""


@pytest.mark.parametrize("kind", BLOCK_LABELS)
def test_new_blocks_are_valid(kind):
    parse_template(dump_template({"blocks": [new_block(kind)]}))


def test_block_list_speaks_plain_language(page):
    texts = []
    for index in range(page.tree.topLevelItemCount()):
        item = page.tree.topLevelItem(index)
        texts.append(item.text(0))
        texts += [item.child(i).text(0) for i in range(item.childCount())]
    assert not any("{{" in text for text in texts)
    assert "Überschrift: [Messschritt: Titel]" in texts


def test_properties_get_the_larger_share_of_the_space(page):
    page.window().resize(1360, 860)
    page.window().show()
    assert page.form_host.height() > page.tree.height()


def test_adding_to_a_repeat_goes_inside_it(page):
    path = repeat_path(page)
    page._select(path)
    page.add_block("text")
    assert page.path() == (path[0], 3)
    assert page.template["blocks"][path[0]]["blocks"][3]["type"] == "text"


def test_a_repeat_cannot_be_nested(page):
    path = repeat_path(page)
    page._select((path[0], 0))
    page.add_block("steps")
    assert len(page.path()) == 1
    assert page._block(page.path())["type"] == "steps"


def test_blocks_move_up_and_down(page):
    first = page.template["blocks"][0]
    page._select((0,))
    page.move_block(1)
    assert page.template["blocks"][1] is first
    assert page.path() == (1,)
    page.move_block(-1)
    assert page.template["blocks"][0] is first


def test_moving_past_the_end_does_nothing(page):
    before = dump_template(page.template)
    page._select((0,))
    page.move_block(-1)
    assert dump_template(page.template) == before


def test_block_moves_into_and_out_of_the_repeat(page):
    path = repeat_path(page)
    block = page.template["blocks"][path[0] + 1]
    page._select((path[0] + 1,))
    page.move_into()
    assert page.path() == (path[0], 3)
    assert page._block(page.path()) is block
    page.move_out()
    assert page.path() == (path[0] + 1,)
    assert page.template["blocks"][path[0] + 1] is block


def test_removing_keeps_a_sensible_selection(page):
    count = page.tree.topLevelItemCount()
    page._select((1,))
    page.remove_block()
    assert page.tree.topLevelItemCount() == count - 1
    assert page.path() == (1,)


def heading_index(page):
    return next(i for i, b in enumerate(page.template["blocks"]) if b["type"] == "heading")


def test_editing_text_changes_the_block_and_its_list_entry(page):
    first = heading_index(page)
    page._select((first,))
    page.text_field.setText("Abnahmeprotokoll")
    assert page.template["blocks"][first]["text"] == "Abnahmeprotokoll"
    assert "Abnahmeprotokoll" in page.tree.topLevelItem(first).text(0)
    assert page.dirty


def test_placeholder_is_inserted_without_typing_code(page):
    page.tree.setCurrentItem(None)
    page.add_block("text")
    page.text_field.clear()
    box = page.form.itemAt(page.form.rowCount() - 2, page.form.ItemRole.FieldRole).widget()
    box.setCurrentIndex(1)
    box.activated.emit(1)
    assert page._block(page.path())["text"] == "{{ customer.name }}"


def measurement_block(page):
    repeat = repeat_path(page)[0]
    index = next(
        i for i, b in enumerate(page.template["blocks"][repeat]["blocks"])
        if b["type"] == "measurements"
    )
    page._select((repeat, index))
    return page._block((repeat, index))


def nodes(page, count):
    return resolve(parse_template(page.current_text()), sample_context(count))


def first_table(found) -> Table:
    return next(n.body for n in found if isinstance(n, Footnoted) and isinstance(n.body, Table))


def test_zero_case_text_is_editable(page):
    measurement_block(page)
    page.none_text.setText("Entfällt.")
    assert Paragraph("Entfällt.") in nodes(page, 0)


def test_zero_case_can_be_hidden(page):
    measurement_block(page)
    page.none_hide.setChecked(True)
    assert not any(isinstance(n, Paragraph) and "gemessen" in n.text for n in nodes(page, 0))


def test_summary_row_can_be_switched_off(page):
    measurement_block(page)
    assert first_table(nodes(page, 4)).summary
    page.many_summary.setChecked(False)
    assert not first_table(nodes(page, 4)).summary


def test_condition_is_chosen_from_a_list(page):
    page._select((0,))
    page.condition.setCurrentIndex(page.condition.findData("device.overdue"))
    assert page.template["blocks"][0]["when"] == "device.overdue"
    page.condition.setCurrentIndex(0)
    assert "when" not in page.template["blocks"][0]


def test_hand_written_condition_survives_the_form(page):
    page.template["blocks"][0]["when"] = "customer.city"
    page._select((1,))
    page._select((0,))
    assert "customer.city" in page.condition.currentText()
    assert page.template["blocks"][0]["when"] == "customer.city"


def test_field_rows_are_editable(page):
    page.tree.setCurrentItem(None)
    page.add_block("fields")
    page.rows_table.item(0, 0).setText("Auftrag")
    assert page._block(page.path())["rows"][0][0] == "Auftrag"


def test_a_field_list_can_take_the_features_of_the_asset(page):
    page.tree.setCurrentItem(None)
    page.add_block("fields")
    assert not page.features_box.isChecked()
    page.features_box.setChecked(True)
    assert page._block(page.path())["features"] == "asset"
    page.features_box.setChecked(False)
    assert "features" not in page._block(page.path())


def test_the_standard_template_shows_the_features_below_the_asset(page):
    assert page.template["blocks"][1]["features"] == "asset"


def test_save_stores_the_change(page):
    first = heading_index(page)
    page._select((first,))
    page.text_field.setText("Abnahmeprotokoll")
    page._save()
    assert stored(page)["blocks"][first]["text"] == "Abnahmeprotokoll"
    assert not page.dirty


def test_source_view_shows_the_blocks_and_takes_changes_back(page):
    first = heading_index(page)
    page._select((first,))
    page.text_field.setText("Aus dem Aufbau")
    page.modes.setCurrentWidget(page.editor)
    assert "Aus dem Aufbau" in page.editor.toPlainText()
    page.editor.setPlainText(page.editor.toPlainText().replace("Aus dem Aufbau", "Aus dem Text"))
    page.modes.setCurrentWidget(page.visual)
    assert "Aus dem Text" in page.tree.topLevelItem(first).text(0)


def test_broken_source_keeps_you_in_the_source_view(page):
    page.modes.setCurrentWidget(page.editor)
    page.editor.setPlainText("blocks:\n  - type: magic\n")
    page.modes.setCurrentWidget(page.visual)
    assert page.modes.currentWidget() is page.editor
    assert "Unbekannter Block" in page.message.text()


def test_save_as_creates_a_second_template_and_delete_removes_it(page, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    page.save_as("Kurzprotokoll")
    assert page.choice.currentText() == "Kurzprotokoll"
    assert len(page.app.db.templates()) == 3
    page._delete()
    assert [t["name"] for t in page.app.db.templates()] == ["Standardprotokoll",
                                                            "Standardprotokoll, kompakt"]
    page.choice.setCurrentIndex(page.choice.findText("Standardprotokoll, kompakt"))
    page._delete()
    assert not page.delete_button.isEnabled()  # the last template stays


def test_unsaved_changes_are_not_lost_silently(page, monkeypatch):
    page.save_as("Zweite")
    first = heading_index(page)
    page._select((first,))
    page.text_field.setText("Ungespeichert")
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.No)
    page.choice.setCurrentIndex(page.choice.findText("Standardprotokoll"))
    assert page.choice.currentText() == "Zweite"
    assert page.template["blocks"][first]["text"] == "Ungespeichert"
