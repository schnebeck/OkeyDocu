# OkeyDocu - tests/test_campaign_templates_ui.py
# Campaign templates in the window: saved from a campaign, taken at the start, learning.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

import pytest

from okeydocu.model import Quantity, ResultValue, Verdict
from okeydocu.ui.campaign_dialog import CampaignDialog
from okeydocu.ui.confirm_overlay import ConfirmOverlay
from okeydocu.ui.template_editor import TemplateEditor
from okeydocu.ui.template_overlays import TemplateCopyOverlay, TemplateLearnOverlay, \
    TemplateSaveOverlay


@pytest.fixture
def plant(app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse 7")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", machine)
    motor = app.db.add_asset(customer, "electric_engine", "Motor", cabinet)
    app.db.add_user("A. Prüfer")
    return {"customer": customer, "machine": machine, "cabinet": cabinet, "motor": motor}


def measure(app, campaign, asset_id, minute, function="riso"):
    value = ResultValue(function, function.upper(), Quantity.parse("200MΩ"), Verdict.PASSED)
    return app.service.add_measurement(campaign, function, [value],
                                       datetime(2026, 11, 14, 9, minute), Verdict.PASSED,
                                       asset_id=asset_id)


@pytest.fixture
def template(window, app, plant, monkeypatch):
    first = app.service.create(plant["machine"], "Erstprüfung", "Prüfer")
    measure(app, first, plant["motor"], 1)
    measure(app, first, plant["cabinet"], 2, "rlo")
    app.service.close(first)
    page = window.campaign
    page.refresh()
    page.show_campaign(first)
    monkeypatch.setattr(TemplateSaveOverlay, "exec", lambda overlay: 1)
    page.template_action.trigger()
    return app.service.templates()[0].key


def start_with(window, monkeypatch, asset_id, key):
    def fill(dialog):
        dialog.asset.setCurrentIndex(dialog.asset.findData(asset_id))
        dialog.template.setCurrentIndex(dialog.template.findData(key))
        return 1

    monkeypatch.setattr(CampaignDialog, "exec", fill)
    window.campaign.new_campaign()
    return window.campaign.campaign_id


def test_a_campaign_becomes_a_template_and_starts_the_next(window, app, plant, template,
                                                           monkeypatch):
    assert app.service.templates()[0].title == "Erstprüfung"
    campaign = start_with(window, monkeypatch, plant["machine"], template)
    page = window.campaign
    assert [step.asset_id for _, step in app.service.points(campaign)] == \
        [plant["motor"], plant["cabinet"]]
    assert page.values.table.rowCount() == 2  # both points open, in grey
    reading = measure(app, campaign, plant["motor"], 5)
    app.service.rematch(campaign)
    page.follow_points(campaign, reading)
    assert page.place_target(campaign) == plant["cabinet"]


def test_another_installation_gets_the_tree_under_the_names_given(window, app, plant, template,
                                                                  monkeypatch):
    other = app.db.add_asset(plant["customer"], "machine", "Presse 8")
    monkeypatch.setattr(TemplateCopyOverlay, "exec", lambda overlay: (
        overlay.table.item(0, 1).setText("=K8"), 1)[1])
    campaign = start_with(window, monkeypatch, other, template)
    made = [app.db.asset(step.asset_id) for _, step in app.service.points(campaign)]
    assert made[1]["identifier"] == "=K8" and made[1]["parent_id"] == other


def test_open_template_points_are_edited_and_learned_on_confirming(window, app, plant, template,
                                                                   monkeypatch):
    campaign = start_with(window, monkeypatch, plant["machine"], template)
    page = window.campaign
    measure(app, campaign, plant["cabinet"], 1, "rlo")
    measure(app, campaign, plant["motor"], 2)
    loose = measure(app, campaign, plant["machine"], 3, "u")
    app.service.rematch(campaign)
    page.values.refresh()
    row = next(r for r in range(page.values.table.rowCount())
               if page.values.table.item(r, 0).data(256) == loose)
    page.values.table.selectRow(row)
    assert page.values.point_action in page.values.point_actions()
    page.values.point_action.trigger()
    learned = []
    monkeypatch.setattr(ConfirmOverlay, "exec", lambda overlay: 1)
    monkeypatch.setattr(TemplateLearnOverlay, "exec",
                        lambda overlay: learned.append(overlay.chosen()) or 1)
    page.show_campaign(campaign)
    page.finish()
    assert app.service.campaign(campaign)["status"] == "closed"
    assert {change.kind for change in learned[0]} == {"new", "order"}
    assert [p["function"] for p in app.service.template(template).points] == ["rlo", "riso", "u"]


def test_the_editor_orders_points_and_renames(qtbot, app, plant, template):
    editor = TemplateEditor(app)
    qtbot.addWidget(editor)
    editor.title.setText("Presse, elektrisch")
    editor.title.textEdited.emit("Presse, elektrisch")
    editor.points.setCurrentRow(1)
    editor._move(-1)
    editor.accept()
    kept = app.service.template(template)
    assert kept.title == "Presse, elektrisch"
    assert [p["function"] for p in kept.points] == ["rlo", "riso"]
