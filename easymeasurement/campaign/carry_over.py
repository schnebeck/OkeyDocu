# EasyMeasurement - easymeasurement/campaign/carry_over.py
# Notes and files of the last confirmed inspection, offered again at the same element.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Taking one over copies it into the open campaign; the sealed one stays as it was. What lay
on a measurement at the element counts as lying on the element, and what lay on the campaign
itself counts as lying on its installation."""

from __future__ import annotations

_EARLIER = """
SELECT a.* FROM attachments a LEFT JOIN measurements m ON m.id = a.measurement_id
WHERE a.campaign_id = ?
  AND (a.asset_id = ? OR (a.asset_id IS NULL AND m.asset_id = ?)
       OR (? AND a.asset_id IS NULL AND a.measurement_id IS NULL))
ORDER BY a.added_at, a.id
"""


class CarryOverMixin:
    def earlier_campaign(self, campaign_id: int):
        """The last confirmed inspection of the same installation, if there is one."""
        campaign = self.campaign(campaign_id)
        previous = self.last_closed(campaign["asset_id"])
        return previous if previous and previous["id"] != campaign_id else None

    def earlier_attachments(self, campaign_id: int, asset_id: int) -> list:
        """What that inspection kept at this element and this campaign does not have yet."""
        previous = self.earlier_campaign(campaign_id)
        if previous is None:
            return []
        top = asset_id == self.campaign(campaign_id)["asset_id"]
        rows = self.db.query(_EARLIER, previous["id"], asset_id, asset_id, top)
        have = self.attachments(campaign_id, asset_id=asset_id)
        files = {row["sha256"] for row in have if row["sha256"]}
        notes = {row["text"] for row in have if row["kind"] == "comment"}
        return [row for row in rows
                if not (row["sha256"] in files if row["sha256"] else row["text"] in notes)]

    def take_over_attachment(self, campaign_id: int, attachment_id: int, asset_id: int) -> int:
        row = self.db.one("SELECT * FROM attachments WHERE id=?", attachment_id)
        if row["kind"] == "comment":
            return self.add_comment(campaign_id, row["text"], asset_id=asset_id)
        source = self.attachment_path(row["campaign_id"], row["file_name"])
        return self.add_attachment(campaign_id, source, asset_id=asset_id, text=row["text"],
                                   name=row["original_name"])
