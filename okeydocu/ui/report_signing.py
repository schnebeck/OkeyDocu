# OkeyDocu - okeydocu/ui/report_signing.py
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

from ..l10n import day, tr
from ..paths import data_dir
from ..reporting.archive import ReportError
from ..reporting.nss import parse
from ..reporting.sign import CertificateInfo, PdfSigner, SigningError, certificate_info, signer_for
from . import pinentry
from .key_password import password_for
from .nss_chooser import NssChooser
from .common import AppContext, show_error
from .overlay import Overlay


def settings() -> QSettings:
    """Local preferences. Holds the certificate's path, never the key or the passphrase."""
    return QSettings(str(data_dir() / "settings.ini"), QSettings.Format.IniFormat)


def describe(info: CertificateInfo) -> str:
    signer = f"{info.name} ({info.email})" if info.email else info.name
    lines = [tr("Signing as {signer}, issued by {issuer}, valid until {day}.", signer=signer,
                issuer=info.issuer or "–", day=day(info.valid_until))]
    if info.email_only:
        lines.append(tr(
            "This is an email certificate (S/MIME). The signature is technically valid. Whether a"
            " PDF program shows it as trustworthy depends on whether it trusts the issuer."
        ))
    return "\n".join(lines)


class CertificateFields(QWidget):
    """The file or the database stays where it is. The password is asked for by pinentry when
    the report is signed; without pinentry it is typed here."""

    changed = Signal()

    def __init__(self, certificate: str = ""):
        super().__init__()
        self.path = QLineEdit(certificate or settings().value("last_certificate", ""))
        self.path.setPlaceholderText(tr("File .p12 or .pfx, or an NSS database"))
        browse = QPushButton(tr("Choose …"))
        browse.clicked.connect(self._browse)
        nss = QPushButton(tr("NSS …"))
        nss.setToolTip(tr("A certificate from an NSS database, such as the one of Firefox"))
        nss.clicked.connect(self._choose_nss)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.path, 1)
        row.addWidget(browse)
        row.addWidget(nss)
        self.password = ""
        self.passphrase = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.info = QLabel()
        self.info.setWordWrap(True)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow(tr("Certificate"), row)
        form.addRow(tr("Password"), self.passphrase)
        form.setRowVisible(1, not pinentry.available())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(form)
        layout.addWidget(self.info)
        self.path.textChanged.connect(self._forget)
        self.passphrase.textChanged.connect(self._forget)
        self.passphrase.editingFinished.connect(self._show_owner)
        self.info.hide()
        if parse(self.path.text()) is not None:
            self._show_owner()

    def _browse(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose certificate"), self.path.text(), "PKCS#12 (*.p12 *.pfx)"
        )
        if path:
            self.path.setText(path)

    def _choose_nss(self) -> None:
        chooser = NssChooser(self, self.path.text())
        if chooser.exec():
            self.path.setText(chooser.reference())
            self._show_owner()

    def _forget(self) -> None:
        self.info.hide()
        self.password = ""
        self.changed.emit()

    def _show_owner(self) -> None:
        """Who the certificate belongs to, where that can be read without asking."""
        try:
            if pinentry.available() and parse(self.path.text()) is None:
                return
            self.info.setText(describe(certificate_info(self.reference(), self.passphrase.text())))
        except SigningError as err:
            self.info.setText(str(err))
        self.info.show()

    def reference(self) -> str:
        return self.path.text().strip()

    def first_field(self, otherwise):
        return self.passphrase if self.passphrase.isVisible() else otherwise

    def ready(self) -> bool:
        return bool(self.path.text().strip())

    def check(self) -> CertificateInfo:
        """Raises SigningError if the certificate, its password or its key will not do; the
        password is asked for here and kept for signing."""
        self.password = password_for(self, self.reference(), self.passphrase.text())
        info = certificate_info(self.reference(), self.password)
        if info.expired:
            raise SigningError(tr("The certificate expired on {day}.", day=day(info.valid_until)))
        if not info.can_sign:
            raise SigningError(tr("This certificate is not issued for signing."))
        return info

    def signer(self) -> PdfSigner:
        return signer_for(self.reference(), self.password or self.passphrase.text())

    def remember(self) -> None:
        settings().setValue("last_certificate", self.path.text().strip())


class SignOverlay(Overlay):
    """Signs a protocol that is already archived. The signed file is a new entry."""

    def __init__(self, parent=None, certificate: str = ""):
        super().__init__(tr("Sign report"), parent)
        self.ok_button.setText(tr("Sign"))
        self.certificate = CertificateFields(certificate)
        self.certificate.changed.connect(self._update)
        self.body.addWidget(self.certificate)
        self._update()

    def first_field(self):
        if not self.certificate.ready():
            return self.certificate.path
        return self.certificate.first_field(self.ok_button)

    def _update(self) -> None:
        self.ok_button.setEnabled(self.certificate.ready())
        missing = "" if self.certificate.ready() else tr("The certificate is still missing.")
        self.hint.setText(missing)

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
