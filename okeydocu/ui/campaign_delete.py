# OkeyDocu - okeydocu/ui/campaign_delete.py
# Deleting an open campaign: asked first, its files to the trash.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile
from PySide6.QtWidgets import QMessageBox

from ..l10n import N_, plural, tr
from .campaign_items import count_text
from .common import AppContext


OPEN = N_("Photos and files go to the trash, readings cannot be restored.")
SEALED = N_(
    "The campaign is closed and sealed. The record and the reports in the archive disappear"
    " with it; the files go to the trash. Reports passed on stay where they are. A deletion"
    " note keeps the seal chain of the other campaigns intact."
)


def loss_text(app: AppContext, campaign) -> str:
    """What goes with the campaign, so the question names it."""
    measured = len(app.service.measurements(campaign["id"]))
    photos = len(app.service.photos(campaign["id"]))
    attached = len(app.service.attachments(campaign["id"]))
    reports = len(app.archive.reports(campaign["id"]))
    present = [(count, text) for count, text in (
        (measured, count_text(measured)),
        (photos, plural(photos, "{count} photo", "{count} photos")),
        (attached, plural(attached, "{count} note or file", "{count} notes and files")),
        (reports, plural(reports, "{count} report", "{count} reports")),
    ) if count]
    if not present:
        return tr("The campaign contains nothing yet.")
    parts = [text for _, text in present]
    if len(parts) > 1:
        parts = [tr("{items} and {last}", items=", ".join(parts[:-1]), last=parts[-1])]
    if len(present) == 1 and present[0][0] == 1:
        return tr("{items} is lost with it.", items=parts[0])
    return tr("{items} are lost with it.", items=parts[0])


def ask_delete(parent, app: AppContext, campaign) -> bool:
    """Cancel is the default: Enter alone must not delete anything."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(tr("Delete campaign"))
    sealed = campaign["status"] == "closed"
    box.setText(tr("Delete “{title}”?", title=campaign["title"]))
    box.setInformativeText(loss_text(app, campaign) + "\n\n" + tr(SEALED if sealed else OPEN))
    delete = box.addButton(tr("Delete permanently") if sealed else tr("Delete"),
                           QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton(tr("Cancel"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is delete


def dispose(folder: Path) -> bool:
    """To the trash, so a photo deleted by mistake can still be found. False if it stayed."""
    if not folder.exists():
        return True
    return bool(QFile.moveToTrash(str(folder)))
