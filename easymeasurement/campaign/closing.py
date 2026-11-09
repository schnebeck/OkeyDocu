# EasyMeasurement - easymeasurement/campaign/closing.py
# Closing a campaign and checking its seal.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

from .records import IMPORTED, _iso
from .repeat import REPEAT
from .seal import SealCheck, SealState, authenticate, deletion_mark, digest, genuine


class ClosingMixin:
    """From an open campaign to a sealed record."""

    def blockers(self, campaign_id: int) -> list[str]:
        """What still prevents closing the campaign."""
        steps = self.steps(campaign_id)
        if not steps:
            return []
        if self.campaign(campaign_id)["plan_key"] == REPEAT:
            return self.repeat_blockers(campaign_id)
        problems = [
            f"Schritt offen: {self.plan_step(step).title}"
            for step in steps
            if step["status"] in ("pending", "active")
        ]
        unassigned = len(self.open_measurements(campaign_id))
        if unassigned:
            problems.append(f"{unassigned} Messung(en) keinem Schritt zugeordnet")
        return problems

    def close(self, campaign_id: int) -> None:
        """Close and seal. From here on the record can only be read."""
        problems = self.blockers(campaign_id)
        if problems:
            raise ValueError("; ".join(problems))
        closed_at = _iso(self._end_of(campaign_id))
        # The record keeps the signature of today, whatever the person's entry becomes.
        self.db.execute(
            "UPDATE campaigns SET signature=(SELECT signature FROM users WHERE id=user_id)"
            " WHERE id=?", campaign_id,
        )
        seal = digest(self.db, campaign_id, closed_at)
        previous = self.db.one(
            "SELECT seal FROM campaigns WHERE seal != '' ORDER BY sealed_at DESC, id DESC LIMIT 1"
        )
        previous = previous["seal"] if previous else ""
        key = self.seal_key()
        self.db.execute(
            "UPDATE campaigns SET status='closed', closed_at=?, seal=?, seal_previous=?,"
            " seal_mac=?, sealed_at=? WHERE id=?",
            closed_at, seal, previous, authenticate(key, seal, previous) if key else "",
            _iso(datetime.now()), campaign_id,
        )

    def delete_campaign(self, campaign_id: int) -> Path:
        """Gone with its reports. A sealed one leaves a signed note for the seal chain.

        Returns the campaign's folder, which the caller disposes of.
        """
        campaign = self.campaign(campaign_id)
        sealed = campaign["status"] == "closed"
        key = self.seal_key() if sealed and campaign["seal"] else None
        now = _iso(datetime.now())
        with self.db.transaction() as connection:
            if sealed:
                mac = authenticate(key, campaign["seal"], deletion_mark(now)) if key else ""
                connection.execute(
                    "INSERT INTO deleted_campaigns (uuid, title, seal, seal_mac, deleted_at)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (campaign["uuid"], campaign["title"], campaign["seal"], mac, now),
                )
                connection.execute("DELETE FROM reports WHERE campaign_id=?", (campaign_id,))
            connection.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        return self.archive_root / "campaigns" / campaign["uuid"]

    def _previous_problems(self, previous: str, key: bytes | None) -> list[str]:
        """The seal before belongs to a campaign that is still here or was deleted openly."""
        if not previous or self.db.one("SELECT 1 FROM campaigns WHERE seal=?", previous):
            return []
        deleted = self.db.one("SELECT * FROM deleted_campaigns WHERE seal=?", previous)
        if deleted is None:
            return ["Eine früher versiegelte Kampagne fehlt."]
        if key and not (deleted["seal_mac"] and genuine(
                key, deleted["seal"], deletion_mark(deleted["deleted_at"]), deleted["seal_mac"])):
            return ["Der Löschvermerk einer früheren Kampagne ist nicht echt."]
        return []

    def _end_of(self, campaign_id: int) -> datetime:
        """An import ended when it was measured, not when it was reviewed."""
        if self.campaign(campaign_id)["driver"] == IMPORTED:
            latest = self.db.one(
                "SELECT max(local_time) AS moment FROM measurements WHERE campaign_id=?",
                campaign_id,
            )
            if latest["moment"]:
                return datetime.fromisoformat(latest["moment"])
        return datetime.now()

    def check_seal(self, campaign_id: int, thorough: bool = True) -> SealCheck:
        """Compare a closed campaign with its seal.

        `thorough` also reads the photo files and asks for the key. Without it
        the check is fast and needs nothing but the database.
        """
        campaign = self.campaign(campaign_id)
        if campaign["status"] != "closed":
            return SealCheck(SealState.OPEN)
        if not campaign["seal"]:
            return SealCheck(SealState.NOT_SEALED)
        reasons = []
        if digest(self.db, campaign_id, campaign["closed_at"]) != campaign["seal"]:
            reasons.append("Die Daten stimmen nicht mehr mit dem Siegel überein.")
        previous = campaign["seal_previous"]
        reasons += self._previous_problems(previous, self.seal_key() if thorough else None)
        if thorough:
            reasons += self._photo_problems(campaign_id)
            key = self.seal_key()
            if key and campaign["seal_mac"]:
                if not genuine(key, campaign["seal"], previous, campaign["seal_mac"]):
                    reasons.append("Das Siegel ist nicht echt.")
            elif key:
                reasons.append("Das Siegel wurde ohne Schlüssel gesetzt oder entfernt.")
        if reasons:
            return SealCheck(SealState.TAMPERED, tuple(reasons))
        if thorough and self.seal_key() and campaign["seal_mac"]:
            return SealCheck(SealState.INTACT)
        return SealCheck(SealState.UNVERIFIED)

    def _photo_problems(self, campaign_id: int) -> list[str]:
        files = [
            (self.photo_path(campaign_id, row["file_name"]), row["sha256"], "Foto")
            for row in self.photos(campaign_id)
        ] + [
            (self.attachment_path(campaign_id, row["file_name"]), row["sha256"], "Anlage")
            for row in self.attachments(campaign_id) if row["file_name"]
        ]
        problems = []
        for path, sha256, label in files:
            if not path.exists():
                problems.append(f"{label} fehlt: {path.name}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != sha256:
                problems.append(f"{label} wurde verändert: {path.name}")
        return problems
