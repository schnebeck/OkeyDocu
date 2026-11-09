# EasyMeasurement - easymeasurement/ui/campaign_confirm.py
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
from .campaign_delete import ask_delete, dispose
from .common import run_busy, show_error
from .confirm_overlay import ConfirmOverlay
from ..reporting.language import SOURCE
from .report_signing import open_report, settings

WEAK_SEAL = (
    "Der Datensatz ist abgeschlossen, aber der Schlüssel aus KWallet war nicht erreichbar.\n\n"
    "Das Siegel erkennt damit nur zufällige Änderungen, keine gezielte Manipulation."
)
LATER = "Das Protokoll lässt sich unter „Protokolle“ erneut erstellen und signieren."


class CampaignConfirm:
    """The draft shows the protocol as it stands; confirming makes it final."""

    def show_draft(self) -> None:
        campaign = self._campaign()
        templates = self.app.db.templates()
        if campaign is None or campaign["status"] != "open" or not templates:
            return
        self.values.editor.apply()  # the draft shows what was typed, too
        language = settings().value("protocol_language", SOURCE)
        try:
            path = self.app.archive.draft(campaign["id"], templates[0]["body"], language)
        except (ReportError, TemplateError) as err:
            show_error(self, str(err))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def delete_campaign(self) -> None:
        campaign = self._campaign()
        if campaign is None or not ask_delete(self, self.app, campaign):
            return
        if campaign["status"] == "closed":
            run_busy(self, "Hole den Siegelschlüssel …", self.app.service.seal_key)
        self.values.editor.discard()
        if self.live_id == campaign["id"]:
            self._end_session()
        folder = self.app.service.delete_campaign(campaign["id"])
        self.list.refresh()
        self.show_home()
        self.changed.emit()
        if dispose(folder):
            self.notice.setText(f"„{campaign['title']}“ gelöscht.")
        else:
            self.notice.setText(
                f"„{campaign['title']}“ gelöscht. Ihre Dateien liegen noch in {folder}."
            )

    def finish(self) -> None:
        campaign = self._campaign()
        if campaign is None or campaign["status"] != "open":
            return
        self.values.editor.apply()  # nothing typed may be lost to the seal
        overlay = ConfirmOverlay(self.app, campaign, self)
        if not overlay.exec():
            return
        closing = self.campaign_id
        # Disconnected first: a reading still on its way must not meet a closed record.
        if self.live_id == closing:
            self._end_session()
        run_busy(self, "Versiegele den Datensatz …", self.app.service.seal_key)
        self.app.service.close(closing)
        (self.app.service.folder(closing) / "drafts" / "entwurf.pdf").unlink(missing_ok=True)
        outcome = self._file_protocol(closing, overlay)
        self.refresh()
        self.changed.emit()
        self.reports_changed()
        if not self.app.service.campaign(closing)["seal_mac"]:
            show_error(self, WEAK_SEAL)
        if outcome:
            self.notice.setText(f'{outcome} <a href="report">Öffnen</a>')

    def _file_protocol(self, campaign_id: int, overlay: ConfirmOverlay) -> str:
        """The record is closed already, so a failure here loses nothing."""
        try:
            overlay.language.remember()
            report = self.app.archive.generate(
                campaign_id, overlay.template.currentText(), overlay.template.currentData(),
                overlay.language.code(),
            )
            if not overlay.signing():
                return "Protokoll abgelegt."
            self.app.archive.sign(report, overlay.certificate.signer())
        except (ReportError, TemplateError, SigningError) as err:
            show_error(self, f"Die Kampagne ist abgeschlossen und versiegelt, aber:\n{err}\n\n{LATER}")
            return ""
        overlay.certificate.remember()
        return "Protokoll abgelegt und signiert."

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
