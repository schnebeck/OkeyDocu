# EasyMeasurement - easymeasurement/campaign/attachments.py
# Comments, images and PDFs on a measurement or a place of the installation.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from ..l10n import tr
from .records import _iso

ATTACHMENT_KINDS = {
    ".pdf": "pdf", ".jpg": "image", ".jpeg": "image", ".png": "image", ".heic": "image",
}


class AttachmentError(Exception):
    """The file cannot be attached."""


class AttachmentMixin:
    """An attachment belongs to its campaign, so a closed record stays complete.

    Removing takes it off its measurement or place and leaves it loose in the
    campaign. Deleting ends it, and with it the file.
    """

    def attachments(
        self, campaign_id: int, measurement_id: int | None = None, asset_id: int | None = None
    ):
        sql, args = "SELECT * FROM attachments WHERE campaign_id=?", [campaign_id]
        if measurement_id is not None:
            sql, args = sql + " AND measurement_id=?", [*args, measurement_id]
        if asset_id is not None:
            sql, args = sql + " AND asset_id=?", [*args, asset_id]
        return self.db.query(sql + " ORDER BY added_at, id", *args)

    def loose_attachments(self, campaign_id: int):
        return self.db.query(
            "SELECT * FROM attachments WHERE campaign_id=? AND measurement_id IS NULL"
            " AND asset_id IS NULL ORDER BY added_at, id", campaign_id,
        )

    def attachment_path(self, campaign_id: int, file_name: str) -> Path:
        return self.folder(campaign_id) / "attachments" / file_name

    def add_comment(
        self, campaign_id: int, text: str, measurement_id: int | None = None,
        asset_id: int | None = None,
    ) -> int:
        return self.db.execute(
            "INSERT INTO attachments (campaign_id, measurement_id, asset_id, kind, text, added_at)"
            " VALUES (?, ?, ?, 'comment', ?, ?)",
            campaign_id, measurement_id, asset_id, text, _iso(datetime.now()),
        )

    def add_attachment(
        self, campaign_id: int, source: Path, measurement_id: int | None = None,
        asset_id: int | None = None, text: str = "", name: str = "",
    ) -> int:
        """`name` is the file's name as shown; by default the name of `source`."""
        kind = ATTACHMENT_KINDS.get(source.suffix.lower())
        if kind is None:
            raise AttachmentError(
                tr("{name}: only pictures and PDF files can be attached.", name=source.name))
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        file_name = f"{digest[:12]}{source.suffix.lower()}"
        attachment = self.db.execute(
            "INSERT INTO attachments (campaign_id, measurement_id, asset_id, kind, text, file_name,"
            " original_name, sha256, added_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            campaign_id, measurement_id, asset_id, kind, text, file_name, name or source.name,
            digest,
            _iso(datetime.now()),
        )
        target = self.attachment_path(campaign_id, file_name)
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(source, target)
        return attachment

    def remove_attachment(self, attachment_id: int) -> None:
        self.db.execute(
            "UPDATE attachments SET measurement_id=NULL, asset_id=NULL WHERE id=?", attachment_id
        )

    def delete_attachment(self, attachment_id: int) -> None:
        """The file goes with the last attachment that uses it."""
        row = self.db.one("SELECT * FROM attachments WHERE id=?", attachment_id)
        self.db.execute("DELETE FROM attachments WHERE id=?", attachment_id)
        shared = self.db.one(
            "SELECT 1 FROM attachments WHERE campaign_id=? AND file_name=?",
            row["campaign_id"], row["file_name"],
        )
        if row["file_name"] and not shared:
            self.attachment_path(row["campaign_id"], row["file_name"]).unlink(missing_ok=True)
