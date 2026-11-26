# OkeyDocu - tests/test_machine_inspection_plan.py
# The shipped plan for inspecting the electrical equipment of a machine.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from okeydocu.campaign.plan import load_plans
from okeydocu.l10n import speaking


def plan():
    return next(plan for plan in load_plans() if plan.key == "machine_inspection")


def test_the_plan_is_a_draft_of_questions():
    found = plan()
    assert not found.released
    assert found.steps and all(step.kind == "check" and step.question for step in found.steps)


def test_every_question_names_its_clause_of_the_machine_standard():
    assert all(step.text.startswith("EN 60204-1, ") for step in plan().steps)


def test_it_begins_with_the_documentation_and_the_agreement_with_it():
    keys = [step.key for step in plan().steps]
    documents = [key for key in keys if key.startswith("documentation_")]
    assert keys[:len(documents)] == documents and keys[len(documents)] == "conformity"


def test_no_step_has_the_title_or_the_key_of_another():
    steps = plan().steps
    assert len({step.key for step in steps}) == len(steps)
    assert len({step.title for step in steps}) == len(steps)


def test_every_question_says_how_it_is_checked():
    assert all(step.instructions and all(step.instructions) for step in plan().steps)


def test_a_question_on_the_documentation_names_the_kinds_of_document_that_serve_it():
    for language, annex in (("en", "Annex I"), ("de", "Anhang I")):
        with speaking(language):
            documents = [step for step in plan().steps if step.key.startswith("documentation_")]
        assert len(documents) == 8
        for step in documents:
            how, kinds = step.instructions
            assert annex in kinds and "IEC " in kinds and annex not in how
