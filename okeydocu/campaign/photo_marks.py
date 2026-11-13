# OkeyDocu - okeydocu/campaign/photo_marks.py
# What a photo shows: numbered regions with a text each, and its role in the report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..l10n import N_
from .photo_view import PhotoView

# A photo documents by default; it can point something out or show a defect.
ROLES = {"": N_("Documentation"), "hint": N_("Notice"), "defect": N_("Defect")}


@dataclass
class PhotoMark:
    """A region in fractions of the upright picture, and what it shows."""

    number: int
    x: float
    y: float
    w: float
    h: float
    text: str = ""


class PhotoMarkMixin:
    def photo_marks(self, photo_id: int) -> list[PhotoMark]:
        return [
            PhotoMark(row["number"], row["x"], row["y"], row["w"], row["h"], row["text"])
            for row in self.db.query(
                "SELECT * FROM photo_marks WHERE photo_id=? ORDER BY number", photo_id)
        ]

    def photo_role(self, photo_id: int) -> str:
        return self.db.one("SELECT role FROM photos WHERE id=?", photo_id)["role"]

    def view_of_file(self, path) -> PhotoView | None:
        """The view of the photo stored as `path`, known by its campaign's folder and its
        file name; None for any other file."""
        path = Path(path)
        row = self.db.one(
            "SELECT p.rotation, p.crop FROM photos p JOIN campaigns c ON c.id = p.campaign_id"
            " WHERE c.uuid=? AND p.file_name=?", path.parent.parent.name, path.name)
        return PhotoView.stored(row["rotation"], row["crop"]) if row else None

    def photo_view(self, photo_id: int) -> PhotoView:
        row = self.db.one("SELECT rotation, crop FROM photos WHERE id=?", photo_id)
        return PhotoView.stored(row["rotation"], row["crop"])

    def save_photo_notes(self, photo_id: int, role: str, marks: list[PhotoMark],
                         view: PhotoView | None = None) -> None:
        """Role, marks and how the photo is turned and cut, in one go, as the photo view
        hands them over; the marks are in parts of what `view` shows."""
        with self.db.transaction() as connection:
            connection.execute("UPDATE photos SET role=? WHERE id=?", (role, photo_id))
            if view is not None:
                connection.execute("UPDATE photos SET rotation=?, crop=? WHERE id=?",
                                   (view.rotation, view.crop_text(), photo_id))
            connection.execute("DELETE FROM photo_marks WHERE photo_id=?", (photo_id,))
            for mark in marks:
                connection.execute(
                    "INSERT INTO photo_marks (photo_id, number, x, y, w, h, text)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (photo_id, mark.number, mark.x, mark.y, mark.w, mark.h, mark.text.strip()),
                )
