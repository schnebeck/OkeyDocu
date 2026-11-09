# EasyMeasurement - easymeasurement/reporting/archive.py
# Generates reports into the archive and signs them. Archived files never change.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from ..campaign.service import CampaignService
from .context import build_context
from .language import speaking, tr
from .pdf import render_pdf
from .sign import PdfSigner
from .template import parse_template, resolve


class ReportError(Exception):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReportArchive:
    def __init__(self, service: CampaignService):
        self.service = service
        self.db = service.db

    def reports(self, campaign_id: int | None = None):
        if campaign_id is None:
            return self.db.query("SELECT * FROM reports ORDER BY created_at DESC, id DESC")
        return self.db.query(
            "SELECT * FROM reports WHERE campaign_id=? ORDER BY id DESC", campaign_id
        )

    def path(self, report) -> Path:
        return self.service.folder(report["campaign_id"]) / "reports" / report["file_name"]

    def _refuse_tampered(self, campaign_id: int) -> None:
        check = self.service.check_seal(campaign_id)
        if check.rejected:
            raise ReportError(
                "Der Datensatz wurde nach dem Abschluss verändert und wird abgewiesen.\n"
                + "\n".join(check.reasons)
            )

    def is_intact(self, report) -> bool:
        path = self.path(report)
        return path.exists() and _sha256(path) == report["sha256"]

    def generate(
        self, campaign_id: int, template_name: str, template_body: str, language: str = "de"
    ) -> int:
        """Render a closed campaign to a new archived PDF, keeping template and language."""
        campaign = self.service.campaign(campaign_id)
        if campaign["status"] != "closed":
            raise ReportError("Protokolle werden aus abgeschlossenen Kampagnen erzeugt.")
        self._refuse_tampered(campaign_id)
        folder = self.service.folder(campaign_id) / "reports"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = folder / f"protokoll-{stamp}-{language}.pdf"
        with speaking(language):
            nodes = resolve(parse_template(template_body), build_context(self.service, campaign_id))
            render_pdf(nodes, path, footer=f"{tr('Prüfung')} {campaign['uuid']}")
        return self.db.execute(
            "INSERT INTO reports (campaign_id, template_name, template_body, file_name, sha256,"
            " created_at, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            campaign_id, template_name, template_body, path.name, _sha256(path),
            datetime.now().isoformat(timespec="seconds"), language,
        )

    def draft(self, campaign_id: int, template_body: str, language: str = "de") -> Path:
        """A preview of an open campaign. It is overwritten each time and never archived."""
        if self.service.campaign(campaign_id)["status"] != "open":
            raise ReportError("Ein Entwurf entsteht nur aus einer offenen Kampagne.")
        path = self.service.folder(campaign_id) / "drafts" / "entwurf.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        with speaking(language):
            nodes = resolve(parse_template(template_body), build_context(self.service, campaign_id))
            render_pdf(nodes, path, footer=tr("ENTWURF – nicht gültig"))
        return path

    def sign(self, report_id: int, signer: PdfSigner) -> int:
        """Sign a report. The signed file is a new archive entry; the original stays."""
        report = self.db.one("SELECT * FROM reports WHERE id=?", report_id)
        campaign = self.service.campaign(report["campaign_id"])
        if campaign["driver"] == "simulator":
            raise ReportError("Protokolle mit simulierten Messwerten werden nicht signiert.")
        if report["signed_by"]:
            raise ReportError("Dieses Protokoll ist bereits signiert.")
        if not self.is_intact(report):
            raise ReportError("Die archivierte Datei wurde verändert.")
        self._refuse_tampered(report["campaign_id"])
        source = self.path(report)
        target = source.with_name(f"{source.stem}-signiert.pdf")
        with speaking(report["language"]):
            reason = f"{tr('Prüfprotokoll')} {campaign['title']}"
        signed_by = signer.sign(source, target, reason=reason)
        return self.db.execute(
            "INSERT INTO reports (campaign_id, template_name, template_body, file_name, sha256,"
            " created_at, signed_by, language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            report["campaign_id"], report["template_name"], report["template_body"], target.name,
            _sha256(target), datetime.now().isoformat(timespec="seconds"), signed_by,
            report["language"],
        )
