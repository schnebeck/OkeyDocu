# OkeyDocu - tests/test_machine_function_plan.py
# The shipped plan for the functional tests of the electrical equipment of a machine.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from okeydocu.campaign.plan import load_plans
from okeydocu.l10n import speaking


def plan():
    return next(plan for plan in load_plans() if plan.key == "machine_tests_functional")


def test_the_plan_is_a_draft_of_questions_each_with_its_clause_and_how_to_test():
    found = plan()
    assert not found.released and found.steps
    for step in found.steps:
        assert step.kind == "check" and step.question and step.text.startswith("EN 60204-1, ")
        assert len(step.instructions) == 1 and step.instructions[0]


def test_no_step_has_the_title_or_the_key_of_another():
    steps = plan().steps
    assert len({step.key for step in steps}) == len(steps)
    assert len({step.title for step in steps}) == len(steps)


def test_it_covers_the_emergency_functions_the_start_and_the_return_of_the_supply():
    keys = {step.key for step in plan().steps}
    assert {"emergency_stop_works", "emergency_stop_latches", "emergency_switching_off",
            "stop_overrides_start", "guard_interlocks", "supply_return"} <= keys
    clauses = {step.text for step in plan().steps}
    assert "EN 60204-1, 18.6" in clauses and "EN 60204-1, 7.5" in clauses


def test_it_reads_in_german():
    with speaking("de"):
        found = plan()
        assert found.label.startswith("Maschine – Funktionsprüfungen")
        assert all(step.title != english.title
                   for step, english in zip(found.steps, _english().steps))


def _english():
    with speaking("en"):
        return plan()
