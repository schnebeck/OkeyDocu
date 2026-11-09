# EasyMeasurement - easymeasurement/ui/report_signing.py
# Choosing a certificate, seeing whose it is, and signing an archived protocol with it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..paths import data_dir
from ..reporting.archive import ReportError
from ..reporting.sign import CertificateInfo, Pkcs12Signer, SigningError, inspect_certificate
from .common import AppContext, show_error
from .overlay import Overlay


def settings() -> QSettings:
    """Local preferences. Holds the certificate's path, never the key or the passphrase."""
    return QSettings(str(data_dir() / "settings.ini"), QSettings.Format.IniFormat)


def describe(info: CertificateInfo) -> str:
    lines = [f"Signiert wird als {info.name}"
             + (f" ({info.email})" if info.email else "")
             + f", ausgestellt von {info.issuer or '–'}, gültig bis {info.valid_until:%d.%m.%Y}."]
    if info.email_only:
        lines.append(
            "Das ist ein E-Mail-Zertifikat (S/MIME). Die Signatur ist technisch gültig. Ob ein"
            " PDF-Programm sie als vertrauenswürdig anzeigt, hängt davon ab, ob es dem Aussteller"
            " vertraut."
        )
    return "\n".join(lines)


class CertificateFields(QWidget):
    """The file stays where it is; who it belongs to shows once the password is in."""

    changed = Signal()

    def __init__(self, certificate: str = ""):
        super().__init__()
        self.path = QLineEdit(certificate or settings().value("last_certificate", ""))
        self.path.setPlaceholderText("Datei .p12 oder .pfx")
        browse = QPushButton("Wählen …")
        browse.clicked.connect(self._browse)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        self.passphrase = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.info = QLabel()
        self.info.setWordWrap(True)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Zertifikat", row)
        form.addRow("Passwort", self.passphrase)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self.info)
        self.path.textChanged.connect(self._forget)
        self.passphrase.textChanged.connect(self._forget)
        self.passphrase.editingFinished.connect(self._show_owner)
        self.info.hide()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Zertifikat wählen", self.path.text(), "PKCS#12 (*.p12 *.pfx)"
        )
        if path:
            self.path.setText(path)

    def _forget(self) -> None:
        self.info.hide()
        self.changed.emit()

    def _show_owner(self) -> None:
        try:
            self.info.setText(describe(self.check()))
        except SigningError as err:
            self.info.setText(str(err))
        self.info.show()

    def ready(self) -> bool:
        return bool(self.path.text().strip())

    def check(self) -> CertificateInfo:
        """Raises SigningError if the file, the password or the certificate will not do."""
        info = inspect_certificate(Path(self.path.text().strip()), self.passphrase.text())
        if info.expired:
            raise SigningError(f"Das Zertifikat ist seit {info.valid_until:%d.%m.%Y} abgelaufen.")
        if not info.can_sign:
            raise SigningError("Dieses Zertifikat ist nicht zum Signieren ausgestellt.")
        return info

    def signer(self) -> Pkcs12Signer:
        return Pkcs12Signer(Path(self.path.text().strip()), self.passphrase.text())

    def remember(self) -> None:
        settings().setValue("last_certificate", self.path.text().strip())


class SignOverlay(Overlay):
    """Signs a protocol that is already archived. The signed file is a new entry."""

    def __init__(self, parent=None, certificate: str = ""):
        super().__init__("Protokoll signieren", parent)
        self.ok_button.setText("Signieren")
        self.certificate = CertificateFields(certificate)
        self.certificate.changed.connect(self._update)
        self.body.addWidget(self.certificate)
        self._update()

    def first_field(self):
        return self.certificate.passphrase if self.certificate.ready() else self.certificate.path

    def _update(self) -> None:
        self.ok_button.setEnabled(self.certificate.ready())
        self.hint.setText("" if self.certificate.ready() else "Es fehlt noch das Zertifikat.")

    def accept(self) -> None:
        try:
            self.certificate.check()
        except SigningError as err:
            self.hint.setText(str(err))
            return
        super().accept()


def open_report(app: AppContext, report) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(app.archive.path(report))))


def user_certificate(app: AppContext, campaign) -> str:
    user = app.db.user(campaign["user_id"]) if campaign["user_id"] else None
    return user["certificate_path"] if user else ""


def sign_report(parent, app: AppContext, report) -> bool:
    campaign = app.service.campaign(report["campaign_id"])
    overlay = SignOverlay(parent, user_certificate(app, campaign))
    if not overlay.exec():
        return False
    try:
        app.archive.sign(report["id"], overlay.certificate.signer())
    except (ReportError, SigningError) as err:
        show_error(parent, str(err))
        return False
    overlay.certificate.remember()
    return True
