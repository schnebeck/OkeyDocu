# OkeyDocu - tests/test_skipped_steps.py
# l10n: de
# A step skipped with its reason is no gap in a test; one left open is.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.campaign.plan import parse_plan
from okeydocu.reporting.context import build_context, overall_verdict
from okeydocu.reporting.language import speaking
from okeydocu.reporting.nodes import Fields, Heading
from okeydocu.reporting.template import default_template_text, parse_template, resolve

PLAN = parse_plan("""
key: sight
title: Besichtigung
released: true
steps:
  - {key: a, kind: check, title: "Typschild vorhanden?"}
  - {key: b, kind: check, title: "Drehfeld gekennzeichnet?"}
  - {key: c, function: rlo}
""")
QUESTIONS = parse_plan("""
key: asked
title: Fragen
released: true
steps:
  - {key: a, kind: check, title: "Typschild vorhanden?"}
  - {key: b, kind: check, title: "Drehfeld gekennzeichnet?"}
""")


def started(app, asset, plan, *answers):
    campaign = app.service.create(asset, "Prüfung", "Anna Beispiel", plan)
    for row, given in zip(app.service.steps(campaign), answers):
        if given == "skip":
            app.service.skip_step(row["id"], "kein Drehstrom")
        elif given:
            app.service.answer_step(row["id"], given)
    return campaign


def result(app, campaign) -> str:
    with speaking("de"):
        return overall_verdict(build_context(app.service, campaign)["steps"])


def test_a_question_left_out_with_its_reason_leaves_the_test_passed(app, asset):
    assert result(app, started(app, asset, QUESTIONS, "yes", "skip")) == "Bestanden"


def test_a_missing_answer_leaves_the_test_incomplete(app, asset):
    assert result(app, started(app, asset, QUESTIONS, "yes", "")) == "Nicht vollständig geprüft"


def test_a_question_left_out_never_hides_a_defect(app, asset):
    assert result(app, started(app, asset, QUESTIONS, "no", "skip")) == "Nicht bestanden"


def test_nothing_but_questions_left_out_is_no_pass(app, asset):
    campaign = started(app, asset, QUESTIONS, "skip", "skip")
    assert result(app, campaign) == "Nicht vollständig geprüft"


def test_a_measuring_step_skipped_with_its_reason_leaves_the_test_passed(app, asset):
    campaign = started(app, asset, PLAN, "yes", "yes")
    app.service.skip_step(app.service.steps(campaign)[2]["id"], "kein Zugang")
    assert result(app, campaign) == "Bestanden"
    with speaking("de"):
        nodes = resolve(parse_template(default_template_text()),
                        build_context(app.service, campaign))
    listed = nodes[heads_index(nodes, "Nicht gemessen") + 1]
    assert [reason for _, reason in listed.rows] == ["kein Zugang"]


def test_a_measuring_step_left_open_leaves_the_test_incomplete(app, asset):
    assert result(app, started(app, asset, PLAN, "yes", "yes")) == "Nicht vollständig geprüft"


def test_a_step_skipped_without_a_reason_leaves_the_test_incomplete(app, asset):
    campaign = started(app, asset, PLAN, "yes", "yes")
    app.service.skip_step(app.service.steps(campaign)[2]["id"], "")
    assert result(app, campaign) == "Nicht vollständig geprüft"


def test_the_report_lists_the_question_left_out_with_its_reason(app, asset):
    campaign = started(app, asset, QUESTIONS, "yes", "skip")
    with speaking("de"):
        nodes = resolve(parse_template(default_template_text()),
                        build_context(app.service, campaign))
    heads = [node.text for node in nodes if isinstance(node, Heading)]
    assert "Ausgelassene Prüffragen mit Begründung" in heads and "Nicht gemessen" not in heads
    listed = nodes[heads_index(nodes, "Ausgelassene Prüffragen mit Begründung") + 1]
    assert isinstance(listed, Fields)
    assert list(listed.rows) == [("Drehfeld gekennzeichnet?", "kein Drehstrom")]


def heads_index(nodes, text: str) -> int:
    return next(index for index, node in enumerate(nodes)
                if isinstance(node, Heading) and node.text == text)
