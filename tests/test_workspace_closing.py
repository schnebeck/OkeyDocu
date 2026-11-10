# EasyMeasurement - tests/test_workspace_closing.py
# Finishing a campaign, closed campaigns, and how the seal shows in the window.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from pathlib import Path

from PySide6.QtGui import QDesktopServices

from easymeasurement.reporting.archive import ReportError
from easymeasurement.reporting.context import build_context as report_context
from easymeasurement.reporting.nodes import Letterhead, Notice
from easymeasurement.reporting.template import (
    DRAFT_NOTICE,
    default_template_text,
    parse_template,
    resolve,
)
from easymeasurement.ui.confirm_overlay import ConfirmOverlay

from .test_report_signing import smime_identity
from .workspace_helpers import plan_title, start, with_asset


# Confirming ------------------------------------------------------------------


def confirm(monkeypatch, fill=None):
    def run(overlay):
        if fill:
            fill(overlay)
        return 1

    monkeypatch.setattr(ConfirmOverlay, "exec", run)


def test_confirming_closes_and_files_the_protocol(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    campaign = window.campaign.campaign_id
    confirm(monkeypatch)
    window.campaign.header.finish_button.click()
    assert app.service.campaign(campaign)["status"] == "closed"
    assert len(app.archive.reports(campaign)) == 1
    assert window.campaign.reports.list.count() == 1
    assert window.campaign.notice.text().startswith("Protokoll abgelegt. ")
    assert window.campaign.header.report_button.isVisible()
    assert not window.campaign.header.finish_button.isVisible()


def test_declining_to_confirm_stays_in_the_open_campaign(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    monkeypatch.setattr(ConfirmOverlay, "exec", lambda self: 0)
    window.campaign.header.finish_button.click()
    assert app.service.campaign(window.campaign.campaign_id)["status"] == "open"
    assert window.campaign.pages.currentWidget() is window.campaign.running


def test_open_steps_are_named_and_hold_the_button(window, app, monkeypatch, qtbot):
    with_asset(window, app)
    start(window, monkeypatch, plan_title(window), simulated=True)
    campaign = app.service.campaign(window.campaign.campaign_id)
    overlay = ConfirmOverlay(app, campaign)
    qtbot.addWidget(overlay)
    assert "Schritt offen" in overlay.open_points.text()
    assert not overlay.ok_button.isEnabled()
    assert not overlay.sign.isEnabled()  # simulated values are never signed


def test_confirming_signs_with_the_certificate(window, app, monkeypatch, tmp_path):
    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "geheim")
    with_asset(window, app)
    start(window, monkeypatch)
    campaign = window.campaign.campaign_id

    def fill(overlay):
        overlay.sign.setChecked(True)
        overlay.certificate.path.setText(str(certificate))
        overlay.certificate.passphrase.setText("geheim")

    confirm(monkeypatch, fill)
    window.campaign.finish()
    reports = app.archive.reports(campaign)
    assert [bool(r["signed_by"]) for r in reports] == [True, False]
    assert window.campaign.notice.text().startswith("Protokoll abgelegt und signiert.")


def test_a_wrong_password_closes_nothing(window, app, monkeypatch, tmp_path, qtbot):
    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "geheim")
    with_asset(window, app)
    start(window, monkeypatch)
    overlay = ConfirmOverlay(app, app.service.campaign(window.campaign.campaign_id))
    qtbot.addWidget(overlay)
    overlay.sign.setChecked(True)
    overlay.certificate.path.setText(str(certificate))
    overlay.certificate.passphrase.setText("falsch")
    overlay.accept()
    assert not overlay.accepted
    assert "Passwort" in overlay.hint.text()


def test_a_failure_after_closing_says_what_is_done(window, app, monkeypatch):
    errors = []
    monkeypatch.setattr("easymeasurement.ui.campaign_confirm.show_error", lambda _, t: errors.append(t))
    monkeypatch.setattr(app.archive, "generate", lambda *_: (_ for _ in ()).throw(ReportError("kaputt")))
    with_asset(window, app)
    start(window, monkeypatch)
    confirm(monkeypatch)
    window.campaign.finish()
    assert app.service.campaign(window.campaign.campaign_id)["status"] == "closed"
    assert "abgeschlossen und versiegelt" in errors[0] and "kaputt" in errors[0]


def test_the_draft_shows_the_open_campaign_without_archiving(window, app, monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()))
    with_asset(window, app)
    start(window, monkeypatch)
    campaign = window.campaign.campaign_id
    window.campaign.header.draft_button.click()
    assert opened and opened[0].endswith("entwurf.pdf")
    assert app.archive.reports(campaign) == []
    confirm(monkeypatch)
    window.campaign.finish()
    assert not Path(opened[0]).exists()


def test_the_draft_says_it_is_one(app, asset):
    campaign = app.service.create(asset, "T", "P")
    context = report_context(app.service, campaign)
    nodes = resolve(parse_template(default_template_text()), context)
    assert isinstance(nodes[0], Letterhead) and nodes[1] == Notice(DRAFT_NOTICE)


# Closed campaigns ------------------------------------------------------------


def finished_campaign(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    campaign = window.campaign.campaign_id
    app.service.add_measurement(campaign, "other", [])
    confirm(monkeypatch)
    window.campaign.header.finish_button.click()
    return campaign


def test_closed_campaigns_are_listed_beside_the_open_ones(window, app, monkeypatch):
    finished_campaign(window, app, monkeypatch)
    listing = window.campaign.list
    assert not listing.closed.isHidden()
    assert "Prüfung Halle" in listing.closed.child(0).text(0)
    assert listing.running.isHidden()


def test_closed_campaign_shows_its_values_at_once(window, app, monkeypatch):
    campaign = finished_campaign(window, app, monkeypatch)
    page = window.campaign
    assert page.campaign_id == campaign
    assert page.values.table.rowCount() == 1
    assert page.current_work() is None
    assert page.report_section.isVisible()
    assert not page.values.manual_action.isEnabled()


def test_closed_campaign_leads_to_a_report(window, app, monkeypatch):
    campaign = finished_campaign(window, app, monkeypatch)
    wanted = []
    monkeypatch.setattr(window.reports, "generate_for", wanted.append)
    window.campaign.header.report_button.click()
    assert wanted == [campaign]


def test_a_further_report_appears_with_its_campaign(window, app, monkeypatch):
    campaign = finished_campaign(window, app, monkeypatch)
    app.db.save_template("Standardprotokoll", default_template_text())
    monkeypatch.setattr(
        window.reports, "generate_for",
        lambda c: app.archive.generate(c, "Standardprotokoll", app.db.templates()[0]["body"]),
    )
    window.campaign.make_report()
    reports = window.campaign.reports
    assert reports.list.count() == 2
    assert "Standardprotokoll" in reports.list.item(0).text()
    assert reports.open_button.isEnabled()
    assert app.service.campaign(campaign)["status"] == "closed"


# Sealing in the window -------------------------------------------------------


def test_closing_without_a_key_is_said_out_loud(window, app, monkeypatch):
    errors = []
    monkeypatch.setattr("easymeasurement.ui.campaign_confirm.show_error", lambda _, t: errors.append(t))
    monkeypatch.setattr(app.service, "seal_key", lambda: None)
    finished_campaign(window, app, monkeypatch)
    assert "KWallet" in errors[0]
    assert "ohne Schlüssel" in window.campaign.list.closed.child(0).text(0)


def test_closing_with_a_key_stays_quiet(window, app, monkeypatch):
    errors = []
    monkeypatch.setattr("easymeasurement.ui.campaign_confirm.show_error", lambda _, t: errors.append(t))
    finished_campaign(window, app, monkeypatch)
    assert errors == []


def test_manipulated_campaign_is_marked_in_the_list(window, app, monkeypatch):
    campaign = finished_campaign(window, app, monkeypatch)
    connection = app.db.connection
    connection.execute("DROP TRIGGER campaign_no_reopen")
    connection.execute("UPDATE campaigns SET title='Fälschung' WHERE id=?", (campaign,))
    connection.commit()
    window.campaign.refresh()
    assert "VERÄNDERT" in window.campaign.list.closed.child(0).text(0)


def test_the_filed_protocol_opens_from_the_notice(window, app, monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()))
    finished_campaign(window, app, monkeypatch)
    window.campaign.notice.linkActivated.emit("report")
    assert opened and opened[0].endswith(".pdf")


def test_a_pending_edit_goes_into_the_seal(window, app, monkeypatch):
    with_asset(window, app)
    start(window, monkeypatch)
    campaign = window.campaign.campaign_id
    app.service.add_measurement(campaign, "other", [])
    window.campaign.refresh()
    window.campaign.values.table.selectRow(0)
    window.campaign.values.editor.comment.setPlainText("noch getippt")
    confirm(monkeypatch)
    window.campaign.finish()
    assert app.service.measurements(campaign)[0]["comment"] == "noch getippt"
    assert app.service.campaign(campaign)["status"] == "closed"
