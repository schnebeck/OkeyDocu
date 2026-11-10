# EasyMeasurement - easymeasurement/reporting/archive.py
# Generates reports into the archive and signs them. Archived files never change.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from ..campaign.service import CampaignService
from .context import build_context
from ..devices import is_simulated
from ..l10n import speaking, tr
from .pdf import render_pdf
from .sign import PdfSigner
from .template import parse_template, resolve


class ReportError(Exception):
    pass


Runner = Callable[[Callable[[], None]], None]


def _at_once(work: Callable[[], None]) -> None:
    work()


def _render(nodes, path: Path, footer: str, language: str) -> Callable[[], None]:
    """The drawing alone, free of the database, so a runner may move it to another thread;
    the language is set again there, since a new thread starts without it."""
    def work() -> None:
        with speaking(language):
            render_pdf(nodes, path, footer=footer)
    return work


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
                tr("The record was changed after it was completed and is refused.") + "\n"
                + "\n".join(check.reasons)
            )

    def is_intact(self, report) -> bool:
        path = self.path(report)
        return path.exists() and _sha256(path) == report["sha256"]

    def generate(
        self, campaign_id: int, template_name: str, template_body: str, language: str = "de",
        run: Runner = _at_once,
    ) -> int:
        """Render a closed campaign to a new archived PDF, keeping template and language."""
        campaign = self.service.campaign(campaign_id)
        if campaign["status"] != "closed":
            raise ReportError(tr("Reports are created from completed campaigns."))
        self._refuse_tampered(campaign_id)
        folder = self.service.folder(campaign_id) / "reports"
        folder.mkdir(exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        path = folder / f"protokoll-{stamp}-{language}.pdf"
        self.service.tidy_proxies(campaign_id)
        with speaking(language):
            nodes = resolve(parse_template(template_body), build_context(self.service, campaign_id))
            footer = f"{tr('Inspection')} {campaign['uuid']}"
        run(_render(nodes, path, footer, language))
        return self.db.execute(
            "INSERT INTO reports (campaign_id, template_name, template_body, file_name, sha256,"
            " created_at, language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            campaign_id, template_name, template_body, path.name, _sha256(path),
            datetime.now().isoformat(timespec="seconds"), language,
        )

    def draft(self, campaign_id: int, template_body: str, language: str = "de",
              run: Runner = _at_once) -> Path:
        """A preview of an open campaign. It is overwritten each time and never archived."""
        if self.service.campaign(campaign_id)["status"] != "open":
            raise ReportError(tr("A draft is made from an open campaign only."))
        path = self.service.folder(campaign_id) / "drafts" / "entwurf.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        self.service.tidy_proxies(campaign_id)
        with speaking(language):
            nodes = resolve(parse_template(template_body), build_context(self.service, campaign_id))
            footer = tr("DRAFT – not valid")
        run(_render(nodes, path, footer, language))
        return path

    def sign(self, report_id: int, signer: PdfSigner) -> int:
        """Sign a report. The signed file is a new archive entry; the original stays."""
        report = self.db.one("SELECT * FROM reports WHERE id=?", report_id)
        campaign = self.service.campaign(report["campaign_id"])
        if is_simulated(campaign["driver"]):
            raise ReportError(tr("Reports with simulated values are not signed."))
        if report["signed_by"]:
            raise ReportError(tr("This report is already signed."))
        if not self.is_intact(report):
            raise ReportError(tr("The archived file was changed."))
        self._refuse_tampered(report["campaign_id"])
        source = self.path(report)
        target = source.with_name(f"{source.stem}-signiert.pdf")
        with speaking(report["language"]):
            reason = f"{tr('Test report')} {campaign['title']}"
        signed_by = signer.sign(source, target, reason=reason)
        return self.db.execute(
            "INSERT INTO reports (campaign_id, template_name, template_body, file_name, sha256,"
            " created_at, signed_by, language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            report["campaign_id"], report["template_name"], report["template_body"], target.name,
            _sha256(target), datetime.now().isoformat(timespec="seconds"), signed_by,
            report["language"],
        )
