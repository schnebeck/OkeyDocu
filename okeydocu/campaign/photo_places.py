# OkeyDocu - okeydocu/campaign/photo_places.py
# A photo of the campaign laid at an element instead of a measurement.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageOps

from ..l10n import tr
from ..store import CampaignClosed
from .photo_view import PhotoView

QUALITY = 92  # of the picture written where the photo was turned or cut


class PhotoPlaceMixin:
    """A photo belongs to a measurement; at an element lie pictures and files. Laying a
    photo there turns it into such a picture, so it leaves the timeline and the stack."""

    def photo_to_place(self, photo_id: int, asset_id: int) -> int:
        """The picture shows what the photo showed: turned and cut the same way. Marks and
        the role of a hint or a defect belong to a photo and do not go along."""
        photo = self.db.one("SELECT * FROM photos WHERE id=?", photo_id)
        campaign_id = photo["campaign_id"]
        if self.campaign(campaign_id)["status"] != "open":
            raise CampaignClosed(tr("The campaign is ended."))
        source = self.photo_path(campaign_id, photo["file_name"])
        view = PhotoView.stored(photo["rotation"], photo["crop"])
        with TemporaryDirectory() as folder:
            if not view.plain:
                source = self._shown_picture(source, view, Path(folder))
            attachment = self.add_attachment(
                campaign_id, source, asset_id=asset_id, name=photo["original_name"])
        self.delete_photo(photo_id)
        return attachment

    @staticmethod
    def _shown_picture(source: Path, view: PhotoView, folder: Path) -> Path:
        target = folder / f"{source.stem}.jpg"
        with Image.open(source) as image:
            upright = ImageOps.exif_transpose(image).convert("RGB")
            view.apply(upright).save(target, quality=QUALITY)
        return target
