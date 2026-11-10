# EasyMeasurement - easymeasurement/ui/company_form.py
# The own firm: name, address, contact and logo, for the letterhead of every report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
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

from ..l10n import N_, tr
from ..reporting.logo import LogoError, decode_logo, prepare_logo
from .common import AppContext
from .overlay import Overlay
from .template_logo_form import read_image_file

LOGO_PREVIEW = (240, 90)
FIELDS = (
    ("name", N_("Name"), N_("e.g. Sample Electrical Ltd")),
    ("street", N_("Street"), ""),
    ("zip", N_("Postcode"), ""),
    ("city", N_("City"), ""),
    ("phone", N_("Phone"), ""),
    ("email", N_("Email"), ""),
    ("web", N_("Website"), ""),
)


class CompanyForm(Overlay):
    """Kept only on taking it over; templates show it through their letterhead."""

    def __init__(self, app: AppContext, parent=None):
        super().__init__(tr("Company"), parent, 560)
        self.app = app
        stored = app.db.company()
        self.logo = stored["logo"]
        self.ok_button.setText(tr("Apply"))
        self.fields: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for key, label, hint in FIELDS:
            field = QLineEdit(stored[key])
            field.setPlaceholderText(tr(hint) if hint else "")
            self.fields[key] = field
            if key == "zip":
                continue
            if key == "city":
                place = QHBoxLayout()
                self.fields["zip"].setMaximumWidth(90)
                place.addWidget(self.fields["zip"])
                place.addWidget(field, 1)
                form.addRow(tr("Postcode, city"), place)
            else:
                form.addRow(tr(label), field)
        self.preview = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(*LOGO_PREVIEW)
        self.preview.setStyleSheet("border: 1px solid palette(mid);")
        self.choose_button = QPushButton()
        self.choose_button.clicked.connect(self._choose)
        self.remove_button = QPushButton(tr("Remove"))
        self.remove_button.clicked.connect(self._remove)
        buttons = QHBoxLayout()
        buttons.addWidget(self.choose_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch()
        logo = QVBoxLayout()
        logo.setSpacing(4)
        logo.addWidget(self.preview, 0, Qt.AlignmentFlag.AlignLeft)
        logo.addLayout(buttons)
        note = QLabel(tr("In the letterhead of every report, to the right of the title. PNG,"
                         " JPEG, WebP or SVG; transparency is kept."))
        note.setWordWrap(True)
        note.setEnabled(False)
        logo.addWidget(note)
        form.addRow(tr("Logo"), logo)
        self.body.addLayout(form)
        self._show_logo()

    def first_field(self) -> QWidget:
        return self.fields["name"]

    def _show_logo(self) -> None:
        pixmap = QPixmap()
        if self.logo:
            try:
                pixmap.loadFromData(decode_logo(self.logo))
            except LogoError:
                pixmap = QPixmap()
        if pixmap.isNull():
            self.preview.setPixmap(QPixmap())
            self.preview.setText(tr("No logo"))
        else:
            self.preview.setPixmap(pixmap.scaled(
                *LOGO_PREVIEW, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        self.choose_button.setText(tr("Replace …") if self.logo else tr("Choose logo …"))
        self.remove_button.setEnabled(bool(self.logo))

    def take_logo(self, path: Path) -> bool:
        try:
            _, self.logo = prepare_logo(read_image_file(path))
        except (LogoError, OSError) as err:
            self.hint.setText(str(err) if isinstance(err, LogoError)
                              else tr("The file cannot be read."))
            return False
        self.hint.clear()
        self._show_logo()
        return True

    def _choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, tr("Choose logo"), "",
            tr("Images ({patterns})", patterns="*.png *.jpg *.jpeg *.webp *.bmp *.svg"))
        if name:
            self.take_logo(Path(name))

    def _remove(self) -> None:
        self.logo = ""
        self._show_logo()

    def accept(self) -> None:
        self.app.db.save_company(
            **{key: field.text().strip() for key, field in self.fields.items()}, logo=self.logo)
        super().accept()
