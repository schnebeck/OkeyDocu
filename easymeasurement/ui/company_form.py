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

from ..reporting.logo import LogoError, decode_logo, prepare_logo
from .common import AppContext
from .overlay import Overlay
from .template_logo_form import read_image_file

LOGO_PREVIEW = (240, 90)
FIELDS = (
    ("name", "Name", "z. B. Muster Elektrotechnik GmbH"),
    ("street", "Straße", ""),
    ("zip", "PLZ", ""),
    ("city", "Ort", ""),
    ("phone", "Telefon", ""),
    ("email", "E-Mail", ""),
    ("web", "Internet", ""),
)


class CompanyForm(Overlay):
    """Kept only on taking it over; templates show it through their letterhead."""

    def __init__(self, app: AppContext, parent=None):
        super().__init__("Firma", parent, 560)
        self.app = app
        stored = app.db.company()
        self.logo = stored["logo"]
        self.ok_button.setText("Übernehmen")
        self.fields: dict[str, QLineEdit] = {}
        form = QFormLayout()
        for key, label, hint in FIELDS:
            field = QLineEdit(stored[key])
            field.setPlaceholderText(hint)
            self.fields[key] = field
            if key == "zip":
                continue
            if key == "city":
                place = QHBoxLayout()
                self.fields["zip"].setMaximumWidth(90)
                place.addWidget(self.fields["zip"])
                place.addWidget(field, 1)
                form.addRow("PLZ, Ort", place)
            else:
                form.addRow(label, field)
        self.preview = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(*LOGO_PREVIEW)
        self.preview.setStyleSheet("border: 1px solid palette(mid);")
        self.choose_button = QPushButton()
        self.choose_button.clicked.connect(self._choose)
        self.remove_button = QPushButton("Entfernen")
        self.remove_button.clicked.connect(self._remove)
        buttons = QHBoxLayout()
        buttons.addWidget(self.choose_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch()
        logo = QVBoxLayout()
        logo.setSpacing(4)
        logo.addWidget(self.preview, 0, Qt.AlignmentFlag.AlignLeft)
        logo.addLayout(buttons)
        note = QLabel("Im Briefkopf jedes Protokolls rechts neben dem Titel. PNG, JPEG, WebP"
                      " oder SVG; Transparenz bleibt erhalten.")
        note.setWordWrap(True)
        note.setEnabled(False)
        logo.addWidget(note)
        form.addRow("Logo", logo)
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
            self.preview.setText("Kein Logo")
        else:
            self.preview.setPixmap(pixmap.scaled(
                *LOGO_PREVIEW, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))
        self.choose_button.setText("Ersetzen …" if self.logo else "Logo wählen …")
        self.remove_button.setEnabled(bool(self.logo))

    def take_logo(self, path: Path) -> bool:
        try:
            _, self.logo = prepare_logo(read_image_file(path))
        except (LogoError, OSError) as err:
            self.hint.setText(str(err) if isinstance(err, LogoError) else "Die Datei lässt sich"
                              " nicht lesen.")
            return False
        self.hint.clear()
        self._show_logo()
        return True

    def _choose(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Logo wählen", "", "Bilder (*.png *.jpg *.jpeg *.webp *.bmp *.svg)")
        if name:
            self.take_logo(Path(name))

    def _remove(self) -> None:
        self.logo = ""
        self._show_logo()

    def accept(self) -> None:
        self.app.db.save_company(
            **{key: field.text().strip() for key, field in self.fields.items()}, logo=self.logo)
        super().accept()
