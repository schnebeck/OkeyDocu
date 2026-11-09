# EasyMeasurement - easymeasurement/ui/campaign_delete.py
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

from .campaign_list import count_text
from .common import AppContext


OPEN = ("Fotos und Dateien kommen in den Papierkorb, Messwerte lassen sich nicht"
        " wiederherstellen.")
SEALED = (
    "Die Kampagne ist abgeschlossen und versiegelt. Mit ihr verschwinden der Datensatz und die"
    " Protokolle im Archiv; die Dateien kommen in den Papierkorb. Weitergegebene Protokolle bleiben,"
    " wo sie sind. Ein Löschvermerk hält die Siegelkette der übrigen Kampagnen intakt."
)


def _amount(count: int, one: str, many: str) -> str:
    return f"1 {one}" if count == 1 else f"{count} {many}"


def loss_text(app: AppContext, campaign) -> str:
    """What goes with the campaign, so the question names it."""
    measured = len(app.service.measurements(campaign["id"]))
    photos = len(app.service.photos(campaign["id"]))
    attached = len(app.service.attachments(campaign["id"]))
    reports = len(app.archive.reports(campaign["id"]))
    present = [(count, text) for count, text in (
        (measured, count_text(measured)),
        (photos, _amount(photos, "Foto", "Fotos")),
        (attached, _amount(attached, "Notiz oder Datei", "Notizen und Dateien")),
        (reports, _amount(reports, "Protokoll", "Protokolle")),
    ) if count]
    if not present:
        return "Die Kampagne enthält noch nichts."
    parts = [text for _, text in present]
    listed = parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " und " + parts[-1]
    verb = "geht" if len(present) == 1 and present[0][0] == 1 else "gehen"
    return f"{listed} {verb} mit verloren."


def ask_delete(parent, app: AppContext, campaign) -> bool:
    """Cancel is the default: Enter alone must not delete anything."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle("Kampagne löschen")
    sealed = campaign["status"] == "closed"
    box.setText(f"„{campaign['title']}“ löschen?")
    box.setInformativeText(loss_text(app, campaign) + "\n\n" + (SEALED if sealed else OPEN))
    delete = box.addButton("Endgültig löschen" if sealed else "Löschen",
                           QMessageBox.ButtonRole.DestructiveRole)
    cancel = box.addButton("Abbrechen", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()
    return box.clickedButton() is delete


def dispose(folder: Path) -> bool:
    """To the trash, so a photo deleted by mistake can still be found. False if it stayed."""
    if not folder.exists():
        return True
    return bool(QFile.moveToTrash(str(folder)))
