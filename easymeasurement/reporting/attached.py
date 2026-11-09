# EasyMeasurement - easymeasurement/reporting/attached.py
# Notes, images and PDFs on measurements and places, sorted for the report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

WHOLE_CAMPAIGN = "Prüfung allgemein"


@dataclass
class Attached:
    notes: list[str] = field(default_factory=list)
    documents: list[str] = field(default_factory=list)  # file names; the files lie in the record
    images: list[Path] = field(default_factory=list)


@dataclass
class ReportPlace:
    name: str
    attached: Attached


def sort_attached(service, rows) -> Attached:
    attached = Attached()
    for row in rows:
        if row["kind"] == "comment":
            attached.notes.append(row["text"])
        elif row["kind"] == "pdf":
            attached.documents.append(row["original_name"])
        else:
            attached.images.append(service.attachment_path(row["campaign_id"], row["file_name"]))
    return attached


def places(service, campaign_id: int) -> list[ReportPlace]:
    """What lies on a place or on the campaign itself, not on a single measurement."""
    by_place: dict[int | None, list] = {}
    for row in service.attachments(campaign_id):
        if row["measurement_id"] is None:
            by_place.setdefault(row["asset_id"], []).append(row)
    return [
        ReportPlace(
            service.db.asset(asset_id)["name"] if asset_id else WHOLE_CAMPAIGN,
            sort_attached(service, rows),
        )
        for asset_id, rows in by_place.items()
    ]
