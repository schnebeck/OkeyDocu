# OkeyDocu - okeydocu/campaign/photo_values.py
# Photos of a campaign: taking them in, and where each of them belongs.
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

from .photo_proxies import drop_proxy
from .photos import nearest_measurement, read_photo_time, timeline_time
from .records import _iso


class PhotoMixin:
    """A photo stands on the timeline, is pinned to a measurement, or lies on the stack.

    On the timeline it belongs to the nearest measurement. A shift moves all of them,
    a gap moves everything after it. Taking a photo off the timeline never deletes it.
    """

    def photos(self, campaign_id: int):
        return self.db.query(
            "SELECT p.*, m.step_id, m.function FROM photos p"
            " LEFT JOIN measurements m ON m.id = p.measurement_id"
            " WHERE p.campaign_id=? ORDER BY p.taken_at, p.id",
            campaign_id,
        )

    def photos_of(self, measurement_id: int):
        return self.db.query(
            "SELECT * FROM photos WHERE measurement_id=? ORDER BY taken_at, id", measurement_id
        )

    def stacked_photos(self, campaign_id: int):
        return self.db.query(
            "SELECT * FROM photos WHERE campaign_id=? AND placement='stack'"
            " ORDER BY taken_at, id", campaign_id,
        )

    def photo_gaps(self, campaign_id: int):
        return self.db.query(
            "SELECT * FROM photo_gaps WHERE campaign_id=? ORDER BY at, id", campaign_id
        )

    def photo_path(self, campaign_id: int, file_name: str) -> Path:
        return self.folder(campaign_id) / "photos" / file_name

    def photo_paths(self, measurement_id: int) -> list[Path]:
        return [
            self.photo_path(row["campaign_id"], row["file_name"])
            for row in self.photos_of(measurement_id)
        ]

    # Taking photos in ----------------------------------------------------

    def _store_photo(self, campaign_id: int, source: Path, digest: str) -> int:
        target = self.folder(campaign_id) / "photos"
        target.mkdir(exist_ok=True)
        file_name = f"{digest[:12]}{source.suffix.lower()}"
        taken_at, time_source = read_photo_time(source)
        photo_id = self.db.execute(
            "INSERT INTO photos (campaign_id, placement, file_name, original_name, sha256,"
            " taken_at, time_source) VALUES (?, ?, ?, ?, ?, ?, ?)",
            campaign_id, "timeline" if taken_at else "stack", file_name, source.name, digest,
            _iso(taken_at) if taken_at else None, time_source,
        )
        shutil.copy2(source, target / file_name)
        return photo_id

    def _known_photo(self, campaign_id: int, digest: str):
        return self.db.one(
            "SELECT * FROM photos WHERE campaign_id=? AND sha256=?", campaign_id, digest
        )

    def add_photo(self, measurement_id: int, source: Path) -> None:
        """Attach a photo to a chosen measurement, whatever its timestamp says."""
        row = self.db.one("SELECT campaign_id FROM measurements WHERE id=?", measurement_id)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        known = self._known_photo(row["campaign_id"], digest)
        photo = known["id"] if known else self._store_photo(row["campaign_id"], source, digest)
        self.pin_photo(photo, measurement_id)

    def import_photos(self, campaign_id: int, files: list[Path]) -> dict:
        """Put photos on the timeline. One without a usable time goes to the stack."""
        known = {row["sha256"] for row in self.photos(campaign_id)}
        added, duplicates = [], 0
        for source in files:
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            if digest in known:
                duplicates += 1
                continue
            known.add(digest)
            added.append(self._store_photo(campaign_id, source, digest))
        self.assign_timeline(campaign_id)
        matched = sum(
            1 for row in self.photos(campaign_id) if row["id"] in added and row["measurement_id"]
        )
        return {
            "added": len(added), "matched": matched, "open": len(added) - matched,
            "duplicates": duplicates,
        }

    # Where a photo belongs -----------------------------------------------

    def assign_timeline(self, campaign_id: int) -> None:
        """Give every photo on the timeline the measurement nearest to its place."""
        campaign = self.campaign(campaign_id)
        measured = [
            (row["id"], datetime.fromisoformat(row["local_time"]))
            for row in self.measurements(campaign_id)
        ]
        gaps = [
            (datetime.fromisoformat(row["at"]), row["seconds"])
            for row in self.photo_gaps(campaign_id)
        ]
        with self.db.transaction() as connection:
            for row in self.photos(campaign_id):
                if row["placement"] == "timeline":
                    moment = timeline_time(
                        datetime.fromisoformat(row["taken_at"]), campaign["photo_shift_s"], gaps
                    )
                    connection.execute(
                        "UPDATE photos SET measurement_id=? WHERE id=?",
                        (nearest_measurement(moment, measured), row["id"]),
                    )

    def set_photo_shift(self, campaign_id: int, seconds: float) -> None:
        self.db.execute("UPDATE campaigns SET photo_shift_s=? WHERE id=?", seconds, campaign_id)
        self.assign_timeline(campaign_id)

    def set_photo_start(self, campaign_id: int, start: datetime) -> None:
        """Move the timeline so that its first photo stands at `start`, gaps included."""
        gaps = [
            (datetime.fromisoformat(row["at"]), row["seconds"])
            for row in self.photo_gaps(campaign_id)
        ]
        places = [
            timeline_time(datetime.fromisoformat(row["taken_at"]), 0, gaps)
            for row in self.photos(campaign_id) if row["placement"] == "timeline"
        ]
        if places:
            self.set_photo_shift(campaign_id, (start - min(places)).total_seconds())

    def add_photo_gap(self, campaign_id: int, at: datetime, seconds: float) -> int:
        gap = self.db.execute(
            "INSERT INTO photo_gaps (campaign_id, at, seconds) VALUES (?, ?, ?)",
            campaign_id, _iso(at), seconds,
        )
        self.assign_timeline(campaign_id)
        return gap

    def resize_photo_gap(self, gap_id: int, seconds: float) -> None:
        gap = self.db.one("SELECT * FROM photo_gaps WHERE id=?", gap_id)
        self.db.execute("UPDATE photo_gaps SET seconds=? WHERE id=?", seconds, gap_id)
        self.assign_timeline(gap["campaign_id"])

    def remove_photo_gap(self, gap_id: int) -> None:
        gap = self.db.one("SELECT * FROM photo_gaps WHERE id=?", gap_id)
        self.db.execute("DELETE FROM photo_gaps WHERE id=?", gap_id)
        self.assign_timeline(gap["campaign_id"])

    def pin_photo(self, photo_id: int, measurement_id: int) -> None:
        """A person decided, so the timeline leaves this photo alone."""
        self.db.execute(
            "UPDATE photos SET placement='pinned', measurement_id=? WHERE id=?",
            measurement_id, photo_id,
        )

    def stack_photo(self, photo_id: int) -> None:
        self.db.execute(
            "UPDATE photos SET placement='stack', measurement_id=NULL WHERE id=?", photo_id
        )

    def return_to_timeline(self, photo_id: int) -> None:
        """A photo without a time cannot stand on the timeline and stays where it is."""
        photo = self.db.one("SELECT * FROM photos WHERE id=?", photo_id)
        if photo["taken_at"]:
            self.db.execute("UPDATE photos SET placement='timeline' WHERE id=?", photo_id)
            self.assign_timeline(photo["campaign_id"])

    def delete_photo(self, photo_id: int) -> None:
        photo = self.db.one("SELECT * FROM photos WHERE id=?", photo_id)
        self.db.execute("DELETE FROM photos WHERE id=?", photo_id)
        original = self.photo_path(photo["campaign_id"], photo["file_name"])
        original.unlink(missing_ok=True)
        drop_proxy(original)
