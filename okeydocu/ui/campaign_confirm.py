# OkeyDocu - okeydocu/ui/campaign_confirm.py
# From an open campaign to a confirmed protocol: the draft before, and the one step that ends it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from ..reporting.archive import ReportError
from ..reporting.sign import SigningError
from ..reporting.template import TemplateError
from ..l10n import N_, current, tr
from .campaign_delete import ask_delete, dispose
from .common import run_busy, show_error
from .confirm_overlay import ConfirmOverlay
from .report_signing import open_report, settings

WEAK_SEAL = N_(
    "The record is closed, but the seal key could not be fetched from the password store.\n\n"
    "So the seal only detects accidental changes, not deliberate tampering."
)
DRAWING = N_("Creating the report …")
LATER = N_("The report can be created and signed again under “Reports”.")


class CampaignConfirm:
    """The draft shows the protocol as it stands; confirming makes it final."""

    def show_draft(self) -> None:
        campaign = self._campaign()
        templates = self.app.db.templates()
        if campaign is None or campaign["status"] != "open" or not templates:
            return
        self.values.editor.apply()  # the draft shows what was typed, too
        language = settings().value("protocol_language", current())
        try:
            path = self.app.archive.draft(campaign["id"], templates[0]["body"], language,
                                          lambda work: run_busy(self, tr(DRAWING), work))
        except (ReportError, TemplateError) as err:
            show_error(self, str(err))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def delete_campaign(self) -> None:
        """An empty campaign goes at once; one holding anything is asked about first."""
        campaign = self._campaign()
        if campaign is None:
            return
        if not self.app.service.is_empty(campaign["id"]) and \
                not ask_delete(self, self.app, campaign):
            return
        if campaign["status"] == "closed":
            run_busy(self, tr("Fetching the seal key …"), self.app.service.seal_key)
        self.values.editor.discard()
        if self.live_id == campaign["id"]:
            self._end_session()
        folder = self.app.service.delete_campaign(campaign["id"])
        self.list.refresh()
        self.show_home()
        self.changed.emit()
        if dispose(folder):
            self.notice.setText(tr("“{title}” deleted.", title=campaign["title"]))
        else:
            self.notice.setText(tr("“{title}” deleted. Its files are still in {folder}.",
                                   title=campaign["title"], folder=folder))

    def finish(self) -> None:
        """An empty campaign is never confirmed; it is deleted instead."""
        campaign = self._campaign()
        if campaign is None or campaign["status"] != "open":
            return
        if self.app.service.is_empty(campaign["id"]):
            return
        self.values.editor.apply()  # nothing typed may be lost to the seal
        overlay = ConfirmOverlay(self.app, campaign, self)
        if not overlay.exec():
            return
        closing = self.campaign_id
        # Disconnected first: a reading still on its way must not meet a closed record.
        if self.live_id == closing:
            self._end_session()
        run_busy(self, tr("Sealing the record …"), self.app.service.seal_key)
        self.app.service.close(closing)
        (self.app.service.folder(closing) / "drafts" / "entwurf.pdf").unlink(missing_ok=True)
        outcome = self._file_protocol(closing, overlay)
        self.refresh()
        self.changed.emit()
        self.reports_changed()
        if not self.app.service.campaign(closing)["seal_mac"]:
            show_error(self, tr(WEAK_SEAL))
        if outcome:
            self.notice.setText(f'{outcome} <a href="report">{tr("Open")}</a>')

    def _file_protocol(self, campaign_id: int, overlay: ConfirmOverlay) -> str:
        """The record is closed already, so a failure here loses nothing."""
        try:
            overlay.language.remember()
            report = self.app.archive.generate(
                campaign_id, overlay.template.currentText(), overlay.template.currentData(),
                overlay.language.code(), lambda work: run_busy(self, tr(DRAWING), work),
            )
            if not overlay.signing():
                return tr("Report filed.")
            self.app.archive.sign(report, overlay.certificate.signer())
        except (ReportError, TemplateError, SigningError) as err:
            show_error(self, tr("The campaign is closed and sealed, but:\n{error}\n\n{later}",
                                error=err, later=tr(LATER)))
            return ""
        overlay.certificate.remember()
        return tr("Report filed and signed.")

    def open_newest_report(self) -> None:
        reports = self.app.archive.reports(self.campaign_id) if self.campaign_id else []
        if reports:
            open_report(self.app, reports[0])

    def make_report(self) -> None:
        if self.campaign_id is not None:
            self.report_requested.emit(self.campaign_id)

    def reports_changed(self) -> None:
        if self.campaign_id is not None:
            self.reports.refresh()
