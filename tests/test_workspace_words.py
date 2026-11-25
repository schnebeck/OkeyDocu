# OkeyDocu - tests/test_workspace_words.py
# The words of the workspace: every text names the thing it is about.
# l10n: de
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""A button says what it does and to what, a state says whose it is, and a count that is a
link shows all it counts."""

from datetime import datetime

import pytest
from PySide6.QtWidgets import QMessageBox

from okeydocu.l10n import speaking
from okeydocu.model import Quantity, ResultValue, Verdict

from .workspace_helpers import plan_title, record, start, with_asset


@pytest.fixture
def page(window, app, monkeypatch, qtbot):
    with_asset(window, app)
    with speaking("de"):
        start(window, monkeypatch, simulated=True)
        record(window, app)
        record(window, app)
        yield window.campaign


def fail_one(page, app):
    value = ResultValue("r", "R", Quantity(raw="5 Ω"))
    app.service.add_measurement(page.campaign_id, "rlo", [value], datetime(2026, 5, 4, 9),
                                Verdict.FAILED)
    page.refresh()


def test_the_buttons_of_the_head_name_what_they_work_on(page):
    assert page.header.finish_button.text() == "Kampagne beenden …"
    assert page.header.draft_button.text() == "Protokoll-Vorschau"


def test_the_status_bar_says_whose_state_it_shows(page):
    assert page.summary.text() == "Kampagne offen"


def test_the_head_of_the_table_counts_the_rows_then_says_what_they_share(page):
    assert page.values.count.text() == "2 Messungen"
    shared = page.values.common.text()
    assert "gemeinsam:" in shared and "Datum <b>" in shared
    row = page.values.head.row
    assert row.indexOf(page.values.count) < row.indexOf(page.values.common)


def test_defects_are_said_to_be_the_installations_and_shown_all_at_once(page, app, qtbot):
    assert not page.values.defects_button.isVisible()
    fail_one(page, app)
    assert "1 Mangel an der Anlage" in page.header.checks.text()
    assert page.values.defects_button.isVisible()
    assert page.values.table.rowCount() == 3
    page._follow_check("failed")
    assert page.values.defects_button.isChecked()
    assert page.values.table.rowCount() == 1
    page.values.defects_button.setChecked(False)
    assert page.values.table.rowCount() == 3


def test_the_narrowing_to_defects_belongs_to_its_campaign(page, app):
    fail_one(page, app)
    page.values.defects_button.setChecked(True)
    other = app.service.create(app.db.assets()[0]["id"], "Zweite", "A. Prüfer")
    page.refresh()
    page.show_campaign(other)
    assert not page.values.defects_button.isChecked()
    assert not page.values.defects_button.isVisible()


def test_a_campaign_with_nothing_in_the_way_can_be_ended(page):
    assert page.header.finish_button.isEnabled()
    assert "Beendet und versiegelt die Kampagne" in page.header.finish_button.toolTip()
    assert "✓ Kampagne kann beendet werden" in page.header.checks.text()


def test_ending_waits_for_the_test_plan_and_says_so(window, app, monkeypatch, qtbot):
    with_asset(window, app)
    with speaking("de"):
        start(window, monkeypatch, plan=plan_title(window), simulated=True)
        record(window, app)
        page = window.campaign
        assert not page.header.finish_button.isEnabled()
        assert not page.finish_action.isEnabled()
        tip = page.header.finish_button.toolTip()
        assert tip.startswith("Noch nicht möglich:") and "Messschritt offen" in tip
        checks = page.header.checks.text()
        assert "Messplan: " in checks and "Messschritte offen" in checks
        assert "1 Messung ohne Messschritt" in checks  # and without a location: it belongs nowhere


def test_a_deleted_measurement_leaves_the_list_of_those_without_a_step(window, app, monkeypatch):
    with_asset(window, app)
    with speaking("de"):
        start(window, monkeypatch, plan=plan_title(window), simulated=True)
        record(window, app)
        record(window, app)
        page = window.campaign
        assert page.guided.open_table.rowCount() == 2
        monkeypatch.setattr(QMessageBox, "question",
                            lambda *args, **kwargs: QMessageBox.StandardButton.Yes)
        page.values.table.selectRow(0)
        page.values._delete_measurement()
        assert len(app.service.open_measurements(page.campaign_id)) == 1
        assert page.guided.open_table.rowCount() == 1
