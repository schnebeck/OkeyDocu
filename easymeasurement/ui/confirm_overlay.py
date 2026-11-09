# EasyMeasurement - easymeasurement/ui/confirm_overlay.py
# Confirming a campaign: what will happen, which template, and the certificate to sign with.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QLabel

from ..reporting.language import SOURCE, languages
from ..reporting.sign import SigningError
from .common import AppContext
from .overlay import Overlay
from .report_signing import CertificateFields, settings, user_certificate

WHAT_HAPPENS = (
    "Die Kampagne wird abgeschlossen und versiegelt. Danach lässt sich an den Messungen nichts"
    " mehr ändern, und jede spätere Änderung am Datensatz wird erkannt. Das Protokoll wird als"
    " PDF abgelegt."
)


def _summary(app: AppContext, campaign_id: int) -> str:
    rows = app.service.measurements(campaign_id)
    failed = sum(row["verdict"] == "failed" for row in rows)
    text = "1 Messung" if len(rows) == 1 else f"{len(rows)} Messungen"
    if failed:
        text += f", davon {failed} nicht bestanden"
    return f"<b>{escape(app.service.campaign(campaign_id)['title'])}:</b> {text}."


class TemplateChoice(QComboBox):
    def __init__(self, app: AppContext):
        super().__init__()
        for row in app.db.templates():
            self.addItem(row["name"], row["body"])


class LanguageChoice(QComboBox):
    """The protocol's language, whatever language the program speaks. The last one is kept."""

    def __init__(self):
        super().__init__()
        for code, name in languages().items():
            self.addItem(name, code)
        self.setCurrentIndex(max(0, self.findData(settings().value("protocol_language", SOURCE))))

    def code(self) -> str:
        return self.currentData()

    def remember(self) -> None:
        settings().setValue("protocol_language", self.code())


class ConfirmOverlay(Overlay):
    """One decision: after it the record is final and the protocol lies in the archive."""

    def __init__(self, app: AppContext, campaign, parent=None):
        super().__init__("Protokoll bestätigen", parent, width=580)
        self.ok_button.setText("Bestätigen und ablegen")
        self.problems = app.service.blockers(campaign["id"])
        simulated = campaign["driver"] == "simulator"
        what = QLabel(WHAT_HAPPENS)
        what.setWordWrap(True)
        self.summary = QLabel(_summary(app, campaign["id"]))
        self.summary.setWordWrap(True)
        self.open_points = QLabel()
        self.open_points.setWordWrap(True)
        self.open_points.setTextFormat(Qt.TextFormat.RichText)
        self.template = TemplateChoice(app)
        form = QFormLayout()
        form.addRow("Vorlage", self.template)
        self.language = LanguageChoice()
        form.addRow("Sprache", self.language)
        self.sign = QCheckBox("Mit Zertifikat signieren")
        self.certificate = CertificateFields(user_certificate(app, campaign))
        self.sign.toggled.connect(self.certificate.setVisible)
        self.sign.toggled.connect(lambda: self._update())
        self.certificate.changed.connect(self._update)
        self.sign.setChecked(not simulated and self.certificate.ready())
        self.certificate.setVisible(self.sign.isChecked())
        self.sign.setEnabled(not simulated)
        if simulated:
            self.sign.setText("Signieren entfällt: Die Messwerte sind simuliert.")
        self.body.addWidget(self.summary)
        self.body.addWidget(what)
        self.body.addWidget(self.open_points)
        self.body.addLayout(form)
        self.body.addWidget(self.sign)
        self.body.addWidget(self.certificate)
        self._update()

    def first_field(self):
        if self.sign.isChecked() and self.certificate.ready():
            return self.certificate.passphrase
        return self.ok_button if self.ok_button.isEnabled() else self.cancel_button

    def signing(self) -> bool:
        return self.sign.isChecked()

    def _update(self) -> None:
        missing = list(self.problems)
        if self.template.count() == 0:
            missing.append("Es gibt keine Protokollvorlage.")
        if self.signing() and not self.certificate.ready():
            missing.append("Es fehlt noch das Zertifikat.")
        self.ok_button.setEnabled(not missing)
        self.hint.setText("Noch nicht möglich, siehe oben." if missing else "")
        self.open_points.setText(
            "<b>Noch offen:</b><ul style='margin: 0'>"
            + "".join(f"<li>{escape(text)}</li>" for text in missing) + "</ul>"
        )
        self.open_points.setVisible(bool(missing))

    def accept(self) -> None:
        """A certificate that will not sign stops here, before anything is closed."""
        if self.signing():
            try:
                self.certificate.check()
            except SigningError as err:
                self.hint.setText(str(err))
                return
        super().accept()
