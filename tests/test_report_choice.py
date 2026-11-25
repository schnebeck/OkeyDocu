# OkeyDocu - tests/test_report_choice.py
# l10n: de
# A campaign is given its report template; preview and report are drawn with it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.store import CampaignClosed
from okeydocu.ui.campaign_edit import CampaignEditOverlay
from okeydocu.ui.confirm_overlay import ConfirmOverlay

from .workspace_helpers import record, start, with_asset


@pytest.fixture
def campaign(app, asset):
    app.db.save_template("Ausführlich", "name: Ausführlich\nblocks: []\n")
    app.db.save_template("Kurz", "name: Kurz\nblocks: []\n")
    return app.service.create(asset, "Prüfung", "Anna Beispiel")


def test_a_fresh_installation_starts_with_the_standard_report(app, campaign):
    assert app.db.default_template()["name"] == "Standardprotokoll"
    assert app.service.report_template(campaign)["name"] == "Standardprotokoll"


def test_without_a_default_a_campaign_takes_the_first_template(app, campaign):
    app.db.execute("UPDATE templates SET standard=0")
    first = app.db.templates()[0]["name"]
    assert app.db.default_template()["name"] == first
    assert app.service.report_template(campaign)["name"] == first


def test_a_campaign_that_names_none_takes_the_default_template(app, campaign):
    app.db.set_default_template("Kurz")
    assert app.service.report_template(campaign)["name"] == "Kurz"
    app.db.set_default_template("Ausführlich")
    assert [row["name"] for row in app.db.templates() if row["standard"]] == ["Ausführlich"]


def test_the_template_manager_marks_the_default(window, app, campaign):
    page = window.templates
    page.reload()
    page.choice.setCurrentIndex(page.choice.findText("Kurz"))
    assert page.default_button.isEnabled() and page.default_button.text() == "Als Standard festlegen"
    page.default_button.click()
    assert app.db.default_template()["name"] == "Kurz"
    assert not page.default_button.isEnabled() and page.default_button.text() == "Standardvorlage"
    page.choice.setCurrentIndex(page.choice.findText("Ausführlich"))
    assert page.default_button.isEnabled()


def test_a_new_campaign_is_offered_the_default_template(window, app, campaign):
    from okeydocu.ui.campaign_dialog import CampaignDialog

    app.db.set_default_template("Kurz")
    dialog = CampaignDialog(app, window, plans=window.guided.plans)
    assert dialog.report_template.currentText() == "Kurz"


def test_the_template_given_is_the_one_used(app, campaign):
    app.service.set_report_template(campaign, "Kurz")
    assert app.service.report_template(campaign)["name"] == "Kurz"


def test_a_template_that_is_gone_falls_back_to_the_default(app, campaign):
    app.service.set_report_template(campaign, "Kurz")
    app.db.set_default_template("Ausführlich")
    app.db.execute("DELETE FROM templates WHERE name='Kurz'")
    assert app.service.report_template(campaign)["name"] == "Ausführlich"


def test_an_ended_campaign_keeps_its_template(app, campaign):
    app.service.close(campaign)
    with pytest.raises(CampaignClosed):
        app.service.set_report_template(campaign, "Kurz")


def test_the_properties_of_a_campaign_choose_its_template(window, app, monkeypatch):
    with_asset(window, app)
    app.db.save_template("Kurz", "name: Kurz\nblocks: []\n")
    start(window, monkeypatch)
    record(window, app)
    page = window.campaign

    def choose(overlay):
        overlay.template.setCurrentIndex(overlay.template.findText("Kurz"))
        return 1

    monkeypatch.setattr(CampaignEditOverlay, "exec", choose)
    page.edit_campaign()
    assert app.service.campaign(page.campaign_id)["report_template"] == "Kurz"
    assert "Protokollvorlage: Kurz" in page.header.draft_button.toolTip()
    shown = []
    monkeypatch.setattr(app.archive, "draft",
                        lambda campaign, body, *rest: shown.append(body) or None)
    monkeypatch.setattr("okeydocu.ui.campaign_confirm.QDesktopServices.openUrl", lambda url: True)
    page.show_draft()
    assert shown == ["name: Kurz\nblocks: []\n"]
    ending = ConfirmOverlay(app, app.service.campaign(page.campaign_id), window)
    assert ending.template.currentText() == "Kurz"
