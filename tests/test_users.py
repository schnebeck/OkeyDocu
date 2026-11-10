# EasyMeasurement - tests/test_users.py
# People: who they are, how they are chosen, and what the record keeps of them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from easymeasurement.campaign.service import full_name
from easymeasurement.devices.simulator import SimulatedMeter
from easymeasurement.reporting.context import build_context as report_context
from easymeasurement.store import CampaignClosed
from easymeasurement.ui.campaign_dialog import CampaignDialog
from easymeasurement.ui.user_form import UserForm
from easymeasurement.ui.users import UserChoice


# Who they are ----------------------------------------------------------------


def test_title_and_name_make_the_full_name(app):
    user = app.db.user(app.db.add_user("Erika Muster", "Dipl.-Ing."))
    assert full_name(user) == "Dipl.-Ing. Erika Muster"


def test_name_without_a_title_has_no_stray_space(app):
    assert full_name(app.db.user(app.db.add_user("Erika Muster"))) == "Erika Muster"


def test_unused_person_is_really_removed(app):
    user = app.db.add_user("Erika Muster")
    app.db.remove_user(user)
    assert app.db.user(user) is None


def test_person_with_campaigns_only_leaves_the_choice(app, asset):
    user = app.db.add_user("Erika Muster")
    app.service.create(asset, "T", "Erika Muster", user_id=user)
    app.db.remove_user(user)
    assert app.db.users() == []
    assert app.db.user(user)["archived"] == 1


# Choosing --------------------------------------------------------------------


def test_the_last_person_is_suggested(app, asset):
    first = app.db.add_user("Anna")
    second = app.db.add_user("Berta")
    app.service.create(asset, "T", "Berta", user_id=second)
    assert app.service.last_user_id() == second
    assert first != second


def test_without_any_campaign_the_only_person_is_suggested(app):
    user = app.db.add_user("Anna")
    assert app.service.last_user_id() == user


def test_nobody_to_suggest(app):
    assert app.service.last_user_id() is None


def test_start_needs_a_person_and_says_so(qtbot, app, asset):
    dialog = CampaignDialog(app)
    qtbot.addWidget(dialog)
    assert not dialog.ok_button.isEnabled()
    assert "Prüfer" in dialog.hint.text()


def test_start_is_one_key_away_when_all_is_known(qtbot, app, asset):
    app.db.add_user("Anna")
    dialog = CampaignDialog(app)
    qtbot.addWidget(dialog)
    assert dialog.ok_button.isEnabled()
    assert dialog.title.text().startswith("Prüfung vom")
    assert dialog.tester.current_name() == "Anna"


def test_missing_title_is_named(qtbot, app, asset):
    app.db.add_user("Anna")
    dialog = CampaignDialog(app)
    qtbot.addWidget(dialog)
    dialog.title.clear()
    assert not dialog.ok_button.isEnabled()
    assert "Titel" in dialog.hint.text()


def test_a_person_can_be_added_while_choosing(qtbot, app, monkeypatch):
    def fill(form):
        form.name.setText("Neu Angelegt")
        form.accept()
        return 1

    monkeypatch.setattr(UserForm, "exec", fill)
    choice = UserChoice(app)
    qtbot.addWidget(choice)
    choice.new_button.click()
    assert choice.current_name() == "Neu Angelegt"


# In the record ---------------------------------------------------------------


def test_campaign_keeps_the_name_it_was_done_under(app, asset):
    user = app.db.add_user("Erika Muster", "Dipl.-Ing.")
    campaign = app.service.create(asset, "T", "Dipl.-Ing. Erika Muster", user_id=user)
    app.db.update_user(user, "Erika Neu", "Dr.", None, "", "", "")
    assert app.service.campaign(campaign)["tester"] == "Dipl.-Ing. Erika Muster"


def test_a_pushed_measurement_names_the_person_of_the_campaign(app, asset):
    campaign = app.service.create(asset, "T", "Erika Muster", driver_key="simulator")
    meter = SimulatedMeter()
    pushed = []
    meter.subscribe_live(pushed.append)
    meter.simulate_measurement("u")
    app.service.receive(campaign, pushed[0])
    assert app.service.measurements(campaign)[0]["operator"] == "Erika Muster"


def test_changing_the_person_can_leave_the_measurements_alone(app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    app.service.add_measurement(campaign, "other", [])
    app.service.assign_tester(campaign, app.db.add_user("Berta"))
    assert app.service.campaign(campaign)["tester"] == "Berta"
    assert app.service.measurements(campaign)[0]["operator"] == "Anna"


def test_changing_the_person_for_the_measurements_is_registered(app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    measurement = app.service.add_measurement(campaign, "other", [])
    app.service.assign_tester(campaign, app.db.add_user("Berta"), measurements=True)
    assert app.service.measurements(campaign)[0]["operator"] == "Berta"
    change = app.service.measurement_changes(measurement)[0]
    assert (change["field"], change["old_value"], change["new_value"]) == ("operator", "Anna", "Berta")


def test_who_measured_does_not_mark_the_result_as_changed(app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    app.service.add_measurement(campaign, "other", [])
    app.service.assign_tester(campaign, app.db.add_user("Berta"), measurements=True)
    app.service.close(campaign)
    steps = report_context(app.service, campaign)["steps"]
    assert not steps[0].measurements[0].edited


def test_a_closed_campaign_keeps_its_person(app, asset):
    campaign = app.service.create(asset, "T", "Anna")
    app.service.close(campaign)
    with pytest.raises(CampaignClosed):
        app.service.assign_tester(campaign, app.db.add_user("Berta"))


def test_closing_keeps_the_signature_of_that_day(app, asset):
    user = app.db.add_user("Anna", signature=b"today")
    campaign = app.service.create(asset, "T", "Anna", user_id=user)
    app.service.close(campaign)
    app.db.update_user(user, "Anna", "", b"later", "", "", "")
    assert app.service.campaign(campaign)["signature"] == b"today"
    assert app.service.check_seal(campaign).state.value == "intact"


def test_a_swapped_signature_breaks_the_seal(app, asset):
    user = app.db.add_user("Anna", signature=b"today")
    campaign = app.service.create(asset, "T", "Anna", user_id=user)
    app.service.close(campaign)
    connection = app.db.connection
    connection.execute("DROP TRIGGER campaign_no_reopen")
    connection.execute("UPDATE campaigns SET signature=? WHERE id=?", (b"forged", campaign))
    connection.commit()
    assert app.service.check_seal(campaign).rejected
