# OkeyDocu - okeydocu/ui/photo_to_place.py
# Laying a photo at an element: asked first where the photo would lose something.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from ..l10n import N_, tr

LOSES = N_("This photo carries marks or counts as a hint or a defect. At an element it is a plain"
           " picture: marks and role are lost. Lay it there anyway?")


def place_photo(parent: QWidget, service, photo_id: int, asset_id: int) -> bool:
    """Says whether the photo lies at the element now."""
    if service.photo_role(photo_id) or service.photo_marks(photo_id):
        answer = QMessageBox.question(parent, tr("Photo at an element"), tr(LOSES))
        if answer != QMessageBox.StandardButton.Yes:
            return False
    service.photo_to_place(photo_id, asset_id)
    return True
