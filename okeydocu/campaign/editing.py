# OkeyDocu - okeydocu/campaign/editing.py
# Changing what was recorded, and who answers for a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import datetime

from ..l10n import tr
from ..store import CampaignClosed, ReadingIsFinal
from .assignment import ISSUE_TEXT
from .records import EDITABLE_FIELDS, EDITABLE_VALUE_FIELDS, TEXT_FIELDS, _iso, full_name


CONTACT_COLUMNS = ("department", "contact", "contact_phone", "contact_email")
ORDER_COLUMNS = ("cost_center", "job_number")

class EditingMixin:
    """Corrections to an open campaign, each leaving the trace it needs."""

    # Who does the work ---------------------------------------------------

    def last_user_id(self) -> int | None:
        """Usually the same person as last time, so that is the one to suggest."""
        row = self.db.one(
            "SELECT u.id FROM campaigns c JOIN users u ON u.id = c.user_id WHERE u.archived=0"
            " ORDER BY c.started_at DESC, c.id DESC LIMIT 1"
        )
        if row:
            return row["id"]
        users = self.db.users()
        return users[0]["id"] if users else None

    def assign_tester(self, campaign_id: int, user_id: int, measurements: bool = False) -> None:
        """Change who answers for an open campaign and, with `measurements`, for its readings."""
        if self.campaign(campaign_id)["status"] != "open":
            raise CampaignClosed(tr("The campaign is closed."))
        name = full_name(self.db.user(user_id))
        rows = self.measurements(campaign_id) if measurements else []
        with self.db.transaction() as connection:
            connection.execute(
                "UPDATE campaigns SET user_id=?, tester=? WHERE id=?", (user_id, name, campaign_id)
            )
            for row in rows:
                if row["operator"] != name:
                    connection.execute(
                        "UPDATE measurements SET operator=? WHERE id=?", (name, row["id"])
                    )
                    self._log(connection, row, "edit", "operator", row["operator"], name)

    # What the campaign is about -----------------------------------------

    def misplaced(self, campaign_id: int, asset_id: int) -> int:
        """Measurements and attachments at a place outside `asset_id` and its parts."""
        row = self.db.one(
            "WITH RECURSIVE tree(id) AS (SELECT ? UNION"
            " SELECT a.id FROM assets a JOIN tree t ON a.parent_id = t.id)"
            " SELECT (SELECT count(*) FROM measurements WHERE campaign_id=?"
            "         AND asset_id IS NOT NULL AND asset_id NOT IN (SELECT id FROM tree))"
            "      + (SELECT count(*) FROM attachments WHERE campaign_id=?"
            "         AND asset_id IS NOT NULL AND asset_id NOT IN (SELECT id FROM tree)) AS count",
            asset_id, campaign_id, campaign_id,
        )
        return row["count"]

    def update_campaign(self, campaign_id: int, title: str, asset_id: int) -> None:
        """Title and installation. Nothing recorded may end up outside the installation."""
        campaign = self.campaign(campaign_id)
        if campaign["status"] != "open":
            raise CampaignClosed(tr("The campaign is closed."))
        title = title.strip()
        if not title:
            raise ValueError(tr("The title is missing."))
        if asset_id != campaign["asset_id"] and self.misplaced(campaign_id, asset_id):
            raise ValueError(tr("Measurements or files are at places outside this installation."))
        self.db.execute(
            "UPDATE campaigns SET title=?, asset_id=? WHERE id=?", title, asset_id, campaign_id
        )

    def set_contact(self, campaign_id: int, *values: str) -> None:
        """The customer's department and person for this job, in the order of
        `CONTACT_COLUMNS`; a closed campaign keeps what it had."""
        if self.campaign(campaign_id)["status"] != "open":
            raise CampaignClosed(tr("The campaign is closed."))
        if len(values) != len(CONTACT_COLUMNS):
            raise ValueError(tr("Expected: {columns}", columns=", ".join(CONTACT_COLUMNS)))
        self.db.execute(
            f"UPDATE campaigns SET {', '.join(f'{c}=?' for c in CONTACT_COLUMNS)} WHERE id=?",
            *(value.strip() for value in values), campaign_id,
        )

    def set_order(self, campaign_id: int, *values: str) -> None:
        """The contractor's own account and reference for this job, in the order of
        `ORDER_COLUMNS`. Both belong to one job, so a new campaign starts without them."""
        if self.campaign(campaign_id)["status"] != "open":
            raise CampaignClosed(tr("The campaign is closed."))
        if len(values) != len(ORDER_COLUMNS):
            raise ValueError(tr("Expected: {columns}", columns=", ".join(ORDER_COLUMNS)))
        self.db.execute(
            f"UPDATE campaigns SET {', '.join(f'{c}=?' for c in ORDER_COLUMNS)} WHERE id=?",
            *(value.strip() for value in values), campaign_id,
        )

    def last_contact(self, asset_id: int, before: int | None = None):
        """Department and contact of the customer's latest other campaign that had them."""
        columns = ", ".join(f"c.{column}" for column in CONTACT_COLUMNS)
        return self.db.one(
            f"SELECT {columns} FROM campaigns c JOIN assets a ON a.id = c.asset_id"
            " WHERE a.customer_id = (SELECT customer_id FROM assets WHERE id=?)"
            " AND c.id IS NOT ? AND (c.department <> '' OR c.contact <> '')"
            " ORDER BY c.started_at DESC, c.id DESC LIMIT 1",
            asset_id, before,
        )

    # Changing what was recorded ------------------------------------------

    def _log(
        self, connection, row, action: str, field: str = "", old: str = "", new: str = ""
    ) -> None:
        connection.execute(
            "INSERT INTO measurement_log (campaign_id, measurement_id, device_uid, changed_at,"
            " action, field, old_value, new_value) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (row["campaign_id"], row["id"], row["device_uid"], _iso(datetime.now()), action, field,
             old, new),
        )

    def edit_measurement(
        self, measurement_id: int, changes: dict[str, str] | None = None,
        value_changes: dict[int, dict[str, str]] | None = None,
    ) -> int:
        """Overwrite what may be overwritten. Returns how many fields changed."""
        changes, value_changes = changes or {}, value_changes or {}
        for field in changes:
            if field not in EDITABLE_FIELDS:
                raise ReadingIsFinal(tr("{field} cannot be changed.", field=field))
        for fields in value_changes.values():
            for field in fields:
                if field not in EDITABLE_VALUE_FIELDS:
                    raise ReadingIsFinal(tr("{field} cannot be changed.", field=field))
        row = self.db.one("SELECT * FROM measurements WHERE id=?", measurement_id)
        changed = 0
        with self.db.transaction() as connection:
            for field, new in changes.items():
                if row[field] != new:
                    connection.execute(
                        f"UPDATE measurements SET {field}=? WHERE id=?", (new, measurement_id)
                    )
                    if field not in TEXT_FIELDS:
                        self._log(connection, row, "edit", field, row[field], new)
                    changed += 1
            for value_id, fields in value_changes.items():
                value = connection.execute(
                    "SELECT * FROM measured_values WHERE id=? AND measurement_id=?",
                    (value_id, measurement_id),
                ).fetchone()
                for field, new in fields.items():
                    if value[field] != new:
                        connection.execute(
                            f"UPDATE measured_values SET {field}=? WHERE id=?", (new, value_id)
                        )
                        if field not in TEXT_FIELDS:
                            self._log(
                                connection, row, "edit", f"{value['key']}.{field}", value[field],
                                new,
                            )
                        changed += 1
        if "function" in changes:
            self.rematch(row["campaign_id"])
        return changed

    def delete_measurement(self, measurement_id: int) -> None:
        """Measuring a point twice and deleting one is normal, so this leaves no note.

        Only the instrument's ID is kept, so the next fetch does not bring it back.
        """
        row = self.db.one("SELECT * FROM measurements WHERE id=?", measurement_id)
        with self.db.transaction() as connection:
            connection.execute(
                "UPDATE photos SET placement='stack' WHERE measurement_id=? AND placement='pinned'",
                (measurement_id,),
            )
            connection.execute("DELETE FROM measurements WHERE id=?", (measurement_id,))
            self._log(connection, row, "delete")
        self.assign_timeline(row["campaign_id"])
        self.rematch(row["campaign_id"])

    def measurement_changes(self, measurement_id: int):
        """Matched on the reading too: SQLite hands the ID of a deleted row out again."""
        return self.db.query(
            "SELECT l.* FROM measurement_log l LEFT JOIN measurements m ON m.id = l.measurement_id"
            " WHERE l.measurement_id=? AND (m.id IS NULL"
            "  OR (m.device_uid = l.device_uid AND m.campaign_id = l.campaign_id)) ORDER BY l.id",
            measurement_id,
        )

    def assign_manually(self, measurement_id: int, step_id: int | None) -> None:
        self.db.execute(
            "UPDATE measurements SET step_id=?, assignment=?, issue='' WHERE id=?",
            step_id, "manual" if step_id else "open", measurement_id,
        )

    def issue_text(self, row) -> str:
        text = ISSUE_TEXT.get(row["issue"])
        return tr(text) if text else ""
