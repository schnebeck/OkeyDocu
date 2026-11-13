# OkeyDocu - okeydocu/ui/user_form.py
# One person: name, signature and certificate.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

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
from ..reporting.sign import SigningError, inspect_certificate
from .common import AppContext
from .overlay import Overlay
from .signature_pad import SignaturePad


class UserForm(Overlay):
    """One person. A password is only used to look into the certificate, never kept."""

    def __init__(self, app: AppContext, parent=None, user=None):
        super().__init__(tr("Edit user") if user else tr("New user"), parent, 560)
        self.app = app
        self.user = user
        self.saved_id: int | None = None
        self.certificate_name = user["certificate_name"] if user else ""
        self.certificate_until = user["certificate_until"] if user else ""

        self.title_field = QLineEdit(user["title"] if user else "")
        self.title_field.setPlaceholderText(tr("e.g. Dipl.-Ing."))
        self.name = QLineEdit(user["name"] if user else "")
        self.name.setPlaceholderText(tr("First and last name"))
        self.name.textChanged.connect(self._update)

        self.pad = SignaturePad()
        if user:
            self.pad.load(user["signature"])
        self.pad.changed.connect(self._update)  # once the buttons it updates are there
        self.clear_button = QPushButton(tr("Clear"))
        self.clear_button.clicked.connect(self.pad.clear)
        self.file_button = QPushButton(tr("From file …"))
        self.file_button.clicked.connect(self._load_signature)
        self.align_button = QPushButton(tr("Align"), checkable=True)
        self.align_button.setToolTip(tr("Drag the signature onto the line; the mouse wheel makes"
                                        " it larger or smaller."))
        self.align_button.toggled.connect(self.pad.set_aligning)
        pad_buttons = QHBoxLayout()
        pad_buttons.addWidget(self.file_button)
        pad_buttons.addWidget(self.align_button)
        pad_buttons.addWidget(self.clear_button)
        pad_buttons.addStretch()
        signature = QVBoxLayout()
        signature.setSpacing(4)
        signature.addWidget(self.pad)
        signature.addLayout(pad_buttons)

        self.certificate = QLineEdit(user["certificate_path"] if user else "")
        self.certificate.setReadOnly(True)
        self.certificate.setPlaceholderText(tr("For signing the reports, can follow later"))
        self.choose_button = QPushButton(tr("Choose …"))
        self.choose_button.clicked.connect(self._choose_certificate)
        self.remove_button = QPushButton(tr("Remove"))
        self.remove_button.clicked.connect(self._remove_certificate)
        chooser = QHBoxLayout()
        chooser.addWidget(self.certificate, 1)
        chooser.addWidget(self.choose_button)
        chooser.addWidget(self.remove_button)
        self.passphrase = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.passphrase.setPlaceholderText(tr("Certificate password, not stored"))
        self.check_button = QPushButton(tr("Check"))
        self.check_button.clicked.connect(self._check_certificate)
        self.passphrase.returnPressed.connect(self.check_button.click)
        self.unlock = QWidget()
        unlock = QHBoxLayout(self.unlock)
        unlock.setContentsMargins(0, 0, 0, 0)
        unlock.addWidget(self.passphrase, 1)
        unlock.addWidget(self.check_button)
        self.unlock.hide()
        self.certificate_state = QLabel()
        self.certificate_state.setWordWrap(True)
        certificate = QVBoxLayout()
        certificate.setSpacing(4)
        certificate.addLayout(chooser)
        certificate.addWidget(self.unlock)
        certificate.addWidget(self.certificate_state)

        form = QFormLayout()
        form.addRow(tr("Title"), self.title_field)
        form.addRow(tr("Name"), self.name)
        form.addRow(tr("Signature"), signature)
        form.addRow(tr("Certificate"), certificate)
        self.body.addLayout(form)
        self._show_certificate()
        self._update()

    def first_field(self) -> QWidget:
        return self.name

    def _update(self) -> None:
        missing = not self.name.text().strip()
        self.ok_button.setEnabled(not missing)
        self.hint.setText(tr("The name is still missing.") if missing else "")
        self.clear_button.setEnabled(not self.pad.empty)

    def _load_signature(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose signature"), "",
            tr("Images ({patterns})", patterns="*.png *.jpg *.jpeg *.PNG *.JPG *.JPEG")
        )
        if path and not self.pad.load(Path(path).read_bytes()):
            self.hint.setText(tr("This file is not a readable image."))

    def _choose_certificate(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, tr("Choose certificate"), self.certificate.text(), "PKCS#12 (*.p12 *.pfx)"
        )
        if path:
            self.certificate.setText(path)
            self.certificate_name = self.certificate_until = ""
            self.unlock.show()
            self.passphrase.setFocus()
            self._show_certificate()

    def _remove_certificate(self) -> None:
        self.certificate.clear()
        self.certificate_name = self.certificate_until = ""
        self.passphrase.clear()
        self.unlock.hide()
        self._show_certificate()

    def _check_certificate(self) -> None:
        try:
            info = inspect_certificate(Path(self.certificate.text()), self.passphrase.text())
        except SigningError as err:
            self.certificate_state.setText(str(err))
            self.passphrase.selectAll()
            return
        finally:
            self.passphrase.clear()
        self.certificate_name = info.name
        self.certificate_until = info.valid_until.date().isoformat()
        self.unlock.hide()
        self._show_certificate()

    def _show_certificate(self) -> None:
        self.remove_button.setVisible(bool(self.certificate.text()))
        self.certificate_state.setVisible(bool(self.certificate.text()))
        self.certificate_state.setText(certificate_text(
            self.certificate_name, self.certificate_until
        ))

    def accept(self) -> None:
        values = (
            self.name.text().strip(), self.title_field.text().strip(), self.pad.data(),
            self.certificate.text(), self.certificate_name, self.certificate_until,
        )
        if self.user:
            self.app.db.update_user(self.user["id"], *values)
            self.saved_id = self.user["id"]
        else:
            self.saved_id = self.app.db.add_user(
                values[0], values[1], values[2], values[3], values[4], values[5]
            )
        super().accept()


def certificate_text(name: str, until: str) -> str:
    if not until:
        return tr("Not checked yet. The password is only needed when signing.")
    moment = datetime.fromisoformat(until).date()
    if moment < date.today():
        return tr("{name}: expired on {day}", name=name, day=day(moment))
    return tr("{name}, valid until {day}", name=name, day=day(moment))
