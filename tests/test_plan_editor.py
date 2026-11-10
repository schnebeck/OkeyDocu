# EasyMeasurement - tests/test_plan_editor.py
# Creating, correcting and trying out plans, and instructions without a plan.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtWidgets import QMessageBox

from easymeasurement.campaign.plan import parse_plan
from easymeasurement.devices import SelectorPosition
from easymeasurement.l10n import tr
from easymeasurement.ui.campaign_views import AssignPlanOverlay
from easymeasurement.ui.instruction_panel import NO_INSTRUCTION, InstructionPanel
from easymeasurement.ui.plan_editor import PlanEditorPage
from easymeasurement.ui.plan_test_run import PlanTestRun


@pytest.fixture
def editor(qtbot, app):
    page = PlanEditorPage(app)
    qtbot.addWidget(page)
    return page


def stored(app, editor):
    editor.save()
    row = next(r for r in app.db.plans() if r["key"] == editor.data["key"])
    return parse_plan(row["body"])


def test_seeded_plan_is_listed(editor):
    assert editor.plans.count() == 1
    assert editor.steps.count() == 5


def test_new_plan_is_saved_at_once(app, editor):
    editor.new_plan()
    assert editor.plans.count() == 2
    assert editor.title.text() == "Neuer Messplan"
    assert stored(app, editor).steps == ()


def test_a_question_is_written_through_the_form(app, editor):
    editor.new_plan()
    editor.add_step("check")
    editor.form.title.setText("Abdeckung vorhanden?")
    editor.form.title.textEdited.emit("Abdeckung vorhanden?")
    step = stored(app, editor).steps[0]
    assert (step.kind, step.title, step.expected) == ("check", "Abdeckung vorhanden?", "yes")
    assert "Abdeckung" in editor.steps.item(0).text()


def test_form_shows_only_what_a_kind_needs(editor):
    editor.new_plan()
    editor.add_step("note")
    assert not editor.form.form.isRowVisible(editor.form.expected)
    assert not editor.form.form.isRowVisible(editor.form.function)
    editor.add_step("measure")
    assert editor.form.form.isRowVisible(editor.form.function)
    assert not editor.form.form.isRowVisible(editor.form.text)


def test_measuring_point_tells_if_there_is_an_instruction(editor):
    editor.new_plan()
    editor.add_step("measure")
    assert "Sammlung" in editor.form.instruction_state.text()
    editor.form.function.setCurrentIndex(editor.form.function.findData("ures"))
    editor.form.function.activated.emit(editor.form.function.currentIndex())
    assert "noch keine" in editor.form.instruction_state.text()


def test_points_can_be_moved_and_removed(app, editor):
    editor.new_plan()
    for title in ("Eins", "Zwei"):
        editor.add_step("note")
        editor.form.title.setText(title)
        editor.form.title.textEdited.emit(title)
    editor.move_step(-1)
    assert [s.title for s in stored(app, editor).steps] == ["Zwei", "Eins"]
    editor.remove_step()
    assert len(stored(app, editor).steps) == 1


def test_changing_plans_saves_the_one_left(app, editor):
    editor.new_plan()
    editor.title.setText("Mein Plan")
    editor.title.textEdited.emit("Mein Plan")
    key = editor.data["key"]
    editor.plans.setCurrentRow(1 - editor.plans.currentRow())
    assert next(r for r in app.db.plans() if r["key"] == key)["title"] == "Mein Plan"


def test_copy_is_a_draft_of_its_own(app, editor):
    editor.released.setChecked(True)
    editor.copy_plan()
    assert "(Kopie)" in editor.title.text()
    assert not editor.released.isChecked()
    assert len(app.db.plans()) == 2


def test_deleting_asks_first(app, editor):
    editor.delete_button.click()  # the default answer in tests is no
    assert len(app.db.plans()) == 1


def test_deleting_after_confirmation(app, editor, monkeypatch):
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    editor.delete_button.click()
    assert app.db.plans() == []
    assert editor.steps.count() == 0


def test_an_empty_plan_cannot_be_tried(editor):
    editor.new_plan()
    assert not editor.run_button.isEnabled()


def test_a_test_run_leaves_no_trace(qtbot, app, editor):
    editor.run_button.click()
    run = editor.test_runs[0]
    qtbot.addWidget(run)
    assert run.page.steps.count() == 5
    assert app.service.campaigns() == []
    run.close()


def test_a_test_run_takes_simulated_readings(qtbot, app):
    plan = app.service.plans()[0]
    run = PlanTestRun(plan)
    qtbot.addWidget(run)
    page = run.page
    page.device_set.setChecked(True)
    for index in range(page.wiring.total):
        page.wiring.wire_clicked(index)
    page.confirm_button.click()
    page.simulate_button.click()
    service = run.app.service
    assert len(service.measurements(run.campaign_id)) == 1
    run.close()


def test_menu_opens_the_editor(window):
    window.plans_action.trigger()
    assert window.plan_editor.isVisible()


def test_plan_can_be_assigned_to_an_open_campaign(window, app, asset, monkeypatch):
    campaign = app.service.create(asset, "T", "Anna")
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    monkeypatch.setattr(AssignPlanOverlay, "exec", lambda self: 1)
    window.campaign.assign_action.trigger()
    assert len(app.service.steps(campaign)) == 5
    assert window.campaign.plan_section.isVisible()
    assert window.campaign.current_work() is window.guided


def test_a_closed_campaign_offers_no_assignment(window, app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    app.service.close(campaign)
    window.campaign.refresh()
    window.campaign.show_campaign(campaign)
    assert not window.campaign.assign_action.isEnabled()


def test_without_plans_the_overlay_says_so(qtbot):
    overlay = AssignPlanOverlay([])
    qtbot.addWidget(overlay)
    assert not overlay.ok_button.isEnabled()
    assert "keinen Messplan" in overlay.hint.text()


# Instructions without a plan -------------------------------------------------


def test_instruction_shows_wiring_and_text(qtbot):
    panel = InstructionPanel()
    qtbot.addWidget(panel)
    panel.show_function("rlo")
    assert "Drehschalter" in panel.text.text()
    assert panel.wiring.step is not None


def test_a_function_without_instruction_says_so(qtbot):
    panel = InstructionPanel()
    qtbot.addWidget(panel)
    panel.show_function("ures")
    assert panel.text.text() == tr(NO_INSTRUCTION)
    assert panel.wiring.step is None


def test_the_instruction_follows_the_switch(qtbot):
    panel = InstructionPanel()
    qtbot.addWidget(panel)
    panel.show_selector(SelectorPosition("U", frozenset({"u", "u3"})))
    assert panel.choice.currentData() == "u3"
    assert "RISO" not in panel.text.text()


def test_a_position_naming_no_function_keeps_the_instruction(qtbot):
    panel = InstructionPanel()
    qtbot.addWidget(panel)
    panel.show_function("riso")
    panel.show_selector(SelectorPosition("Extra"))
    assert panel.choice.currentData() == "riso"


def test_a_switch_without_an_instruction_says_so(qtbot):
    panel = InstructionPanel()
    qtbot.addWidget(panel)
    panel.show_selector(SelectorPosition("IMD", frozenset({"imd"})))
    assert panel.text.text() == tr(NO_INSTRUCTION)


def test_free_measuring_offers_the_instruction_on_request(window, app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    window.campaign.refresh()
    window.campaign.enter(campaign)
    free = window.campaign.free
    assert not free.instruction.isVisible()
    free.instruction_action.trigger()
    assert free.instruction.isVisible()
