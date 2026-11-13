# OkeyDocu - okeydocu/ui/nss_chooser.py
# Choosing a signing certificate from an NSS database: its folder, then the certificate.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Offered are the certificates of the folder that are valid and have their key in the
database. The database is only read; the folder is free, so the one of Firefox or of another
program can be taken as well."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QComboBox, QFileDialog, QFormLayout, QHBoxLayout, QLineEdit, \
    QPushButton

from ..l10n import day, tr
from ..reporting.certificate_info import CertificateInfo, SigningError
from ..reporting.nss import DEFAULT_FOLDER, NssReference, identities, parse
from .overlay import Overlay


def offer_text(info: CertificateInfo) -> str:
    who = f"{info.name} ({info.email})" if info.email else info.name
    return tr("{who} · {issuer} · until {day}", who=who, issuer=info.issuer or "–",
              day=day(info.valid_until))


class NssChooser(Overlay):
    def __init__(self, parent=None, current: str = ""):
        super().__init__(tr("Certificate from an NSS database"), parent, width=640)
        self.ok_button.setText(tr("Take"))
        known = parse(current)
        self.folder = QLineEdit(str(known.folder if known else DEFAULT_FOLDER))
        self.folder.editingFinished.connect(self._load)
        browse = QPushButton(tr("Choose folder …"))
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        self.certificates = QComboBox()
        self.certificates.currentIndexChanged.connect(lambda _: self._update())
        form = QFormLayout()
        form.addRow(tr("Database folder"), row)
        form.addRow(tr("Certificate"), self.certificates)
        self.body.addLayout(form)
        self.infos: dict[str, CertificateInfo] = {}
        self._load(known.label if known else "")

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, tr("Choose the NSS database folder"),
                                                  self.folder.text())
        if chosen:
            self.folder.setText(chosen)
            self._load()

    def _load(self, keep: str = "") -> None:
        self.certificates.clear()
        self.infos.clear()
        try:
            found = identities(Path(self.folder.text().strip()))
        except SigningError as err:
            self.hint.setText(str(err))
            self._update()
            return
        for label, info in found:
            if not info.expired and info.can_sign:
                self.infos[label] = info
                self.certificates.addItem(offer_text(info), label)
        self.certificates.setCurrentIndex(max(self.certificates.findData(keep), 0))
        self.hint.setText("" if self.infos else tr("No valid certificate with its key here."))
        self._update()

    def _update(self) -> None:
        self.ok_button.setEnabled(self.certificates.currentData() is not None)

    def reference(self) -> str:
        folder = Path(self.folder.text().strip()).expanduser()
        return NssReference(folder, self.certificates.currentData()).text()

    def info(self) -> CertificateInfo:
        return self.infos[self.certificates.currentData()]
