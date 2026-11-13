# EasyMeasurement - tests/test_plan_steps.py
# Plans in the data: kinds of points, instructions, answers, several plans.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from easymeasurement.campaign.plan import load_instructions, load_plans, parse_plan
from easymeasurement.reporting.archive import ReportArchive
from easymeasurement.reporting.context import build_context
from easymeasurement.reporting.template import default_template_text
from easymeasurement.store import CampaignClosed

PLAN = """
key: sight
title: Sichtprüfung
released: true
steps:
  - {key: a, kind: note, title: Vorbereitung, text: Anlage freischalten.}
  - {key: b, kind: check, title: "Abdeckung vorhanden?", text: Alle Seiten prüfen.}
  - {key: c, kind: check, title: "Schäden sichtbar?", expected: "no"}
  - {key: d, function: rlo}
"""


@pytest.fixture
def plan():
    return parse_plan(PLAN)


@pytest.fixture
def campaign(service, asset_id, plan):
    return service.create(asset_id, "T", "Anna", plan)


def rows(service, campaign):
    return service.steps(campaign)


def test_points_know_their_kind(plan):
    assert [step.kind for step in plan.steps] == ["note", "check", "check", "measure"]


def test_a_measuring_step_gets_its_instruction_by_function(plan):
    step = plan.steps[3]
    assert step.title == load_instructions()["rlo"].title
    assert step.selector == "RLO"
    assert step.wiring is not None


def test_a_step_can_say_more_than_its_instruction():
    text = "key: x\ntitle: X\nsteps:\n  - {key: a, function: rlo, title: Eigener Titel}\n"
    assert parse_plan(text).steps[0].title == "Eigener Titel"


def test_a_question_has_no_wiring(plan):
    assert plan.steps[1].wiring is None


def test_every_builtin_measuring_step_has_an_instruction():
    instructions = load_instructions()
    for plan in load_plans():
        assert all(step.function in instructions for step in plan.steps
                   if step.kind == "measure")


def test_draft_says_so_in_its_label():
    assert parse_plan("key: x\ntitle: X\nsteps: []").label == "X (Entwurf)"


def test_released_plan_keeps_its_name(plan):
    assert plan.label == "Sichtprüfung"


def test_seeding_fills_an_empty_store_once(service):
    service.seed_plans()
    count = len(service.db.plans())
    assert count > 0
    service.seed_plans()
    assert len(service.db.plans()) == count


def test_a_plan_without_points_is_not_offered(service):
    service.db.save_plan("empty", "Leer", "key: empty\ntitle: Leer\nsteps: []\n")
    assert service.plans() == []


def test_yes_as_expected_passes(service, campaign):
    step = rows(service, campaign)[1]
    service.answer_step(step["id"], "yes")
    measurement = service.measurements(campaign, step["id"])[0]
    assert measurement["verdict"] == "passed"
    assert measurement["function"] == "visual_inspection"
    assert rows(service, campaign)[1]["status"] == "done"


def test_no_where_yes_is_expected_fails(service, campaign):
    step = rows(service, campaign)[1]
    service.answer_step(step["id"], "no", "fehlt an der Rückseite")
    assert service.measurements(campaign, step["id"])[0]["verdict"] == "failed"
    assert service.step_answer(step["id"]) == ("no", "fehlt an der Rückseite")


def test_no_can_be_the_expected_answer(service, campaign):
    step = rows(service, campaign)[2]
    service.answer_step(step["id"], "no")
    assert service.measurements(campaign, step["id"])[0]["verdict"] == "passed"


def test_answering_again_replaces_the_answer(service, campaign):
    step = rows(service, campaign)[1]
    service.answer_step(step["id"], "no")
    service.answer_step(step["id"], "yes")
    assert len(service.measurements(campaign, step["id"])) == 1
    assert service.step_answer(step["id"]) == ("yes", "")


def test_skipping_takes_back_an_answer_and_keeps_the_reason(service, campaign):
    step = rows(service, campaign)[1]
    service.answer_step(step["id"], "yes")
    service.skip_step(step["id"], "nicht zugänglich")
    assert service.measurements(campaign, step["id"]) == []
    assert service.step_answer(step["id"]) == ("skip", "nicht zugänglich")


def test_answer_after_skipping_clears_the_reason(service, campaign):
    step = rows(service, campaign)[1]
    service.skip_step(step["id"], "nicht zugänglich")
    service.answer_step(step["id"], "yes")
    assert rows(service, campaign)[1]["note"] == ""


def test_no_answer_yet(service, campaign):
    assert service.step_answer(rows(service, campaign)[1]["id"]) == ("", "")


def test_a_second_plan_comes_after_the_first(service, campaign, plan):
    service.assign_plan(campaign, parse_plan("key: y\ntitle: Zweiter\nreleased: true\nsteps:\n"
                                             "  - {key: a, kind: note, title: Ende}\n"))
    steps = rows(service, campaign)
    assert [step["position"] for step in steps] == [0, 1, 2, 3, 4]
    assert steps[-1]["plan_title"] == "Zweiter"
    assert service.campaign(campaign)["plan_title"] == "Sichtprüfung + Zweiter"


def test_a_campaign_without_a_plan_can_get_one(service, asset_id, plan):
    campaign = service.create(asset_id, "T", "Anna")
    service.assign_plan(campaign, plan)
    assert service.campaign(campaign)["plan_key"] == "sight"
    assert len(rows(service, campaign)) == 4


def test_a_closed_campaign_gets_no_plan(service, asset_id, plan):
    campaign = service.create(asset_id, "T", "Anna")
    service.close(campaign)
    with pytest.raises(CampaignClosed):
        service.assign_plan(campaign, plan)


def test_a_corrected_plan_changes_no_campaign(service, campaign):
    service.db.save_plan("sight", "Anders", "key: sight\ntitle: Anders\nsteps: []\n")
    assert service.plan_step(rows(service, campaign)[1]).title == "Abdeckung vorhanden?"


def answered(service, campaign):
    steps = rows(service, campaign)
    service.finish_step(steps[0]["id"])
    service.answer_step(steps[1]["id"], "yes", "alles da")
    service.answer_step(steps[2]["id"], "no")
    service.skip_step(steps[3]["id"], "nicht messbar")


def test_report_leaves_out_notes_and_groups_answers(service, campaign):
    answered(service, campaign)
    steps = build_context(service, campaign)["steps"]
    assert [step.title for step in steps] == ["Sichtprüfung", load_instructions()["rlo"].title]
    assert len(steps[0].measurements) == 2


def test_report_keeps_the_reason_for_a_skipped_question(service, campaign):
    steps = rows(service, campaign)
    service.finish_step(steps[0]["id"])
    service.skip_step(steps[1]["id"], "nicht zugänglich")
    report = build_context(service, campaign)["steps"]
    assert (report[0].title, report[0].note) == ("Abdeckung vorhanden?", "nicht zugänglich")


def test_a_failed_answer_fails_the_report(service, campaign):
    steps = rows(service, campaign)
    service.answer_step(steps[1]["id"], "no")
    assert build_context(service, campaign)["verdict"] == "Nicht bestanden"


def test_answers_print_in_a_report(service, campaign):
    answered(service, campaign)
    service.close(campaign)
    report = ReportArchive(service).generate(campaign, "Standard", default_template_text())
    assert report


def test_shipped_instructions_speak_the_language_of_the_program():
    from easymeasurement.l10n import speaking
    with speaking("en"):
        english = load_instructions()["rlo"]
    with speaking("de"):
        german = load_instructions()["rlo"]
    assert english.title == "Protective conductor continuity"
    assert german.title == "Durchgängigkeit Schutzleiter"
    assert ("Prüfstrom", "0,2 A") in german.settings and ("Test current", "0.2 A") in english.settings
    assert german.wiring.wires == english.wiring.wires  # sockets and terminals keep their ids


def test_a_plan_written_by_hand_keeps_its_words():
    from easymeasurement.l10n import speaking
    with speaking("en"):
        plan = parse_plan("key: x\ntitle: Eigener Plan\nreleased: true\nsteps:\n"
                          "- {key: a, kind: check, title: Schalter geprüft}")
    assert plan.title == "Eigener Plan" and plan.steps[0].title == "Schalter geprüft"


def test_a_shipped_step_speaks_the_language_shown_not_the_one_it_was_assigned_in(service,
                                                                                 asset_id):
    from easymeasurement.l10n import speaking, tr

    campaign = service.create(asset_id, "Sichtprüfung", "Prüfer")
    with speaking("de"):
        visual = next(plan for plan in load_plans() if plan.key == "visual_inspection")
        service.assign_plan(campaign, visual)
        german = service.plan_step(service.steps(campaign)[0]).title
    with speaking("en"):
        english = service.plan_step(service.steps(campaign)[0]).title
    assert english == "Documentation"
    with speaking("de"):
        assert german == tr("Documentation") != english
