# OkeyDocu - tests/test_nss_signing.py
# Signing from an NSS database, and key passwords asked for through pinentry.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QWidget

from okeydocu.reporting import nss
from okeydocu.reporting.nss import NssReference, parse
from okeydocu.reporting.sign import SigningError, certificate_info, needs_password, signer_for
from okeydocu.ui import key_password, pinentry

from .nss_helpers import LABEL, make_database

try:
    nss._module_path()
    HAVE_NSS = True
except SigningError:
    HAVE_NSS = False
needs_nss = pytest.mark.skipif(not HAVE_NSS, reason="needs NSS")

FAKE = """#!{python}
import sys
print("OK ready", flush=True)
for line in sys.stdin:
    if line.startswith("GETPIN"):
        print({answer!r}, flush=True)
        if not {answer!r}.startswith("D "):
            continue
    print("OK", flush=True)
"""


def fake_pinentry(tmp_path, answer: str) -> str:
    program = tmp_path / "pinentry"
    program.write_text(FAKE.format(python=sys.executable, answer=answer))
    program.chmod(0o755)
    return str(program)


def small_pdf(path: Path) -> Path:
    from reportlab.pdfgen import canvas

    drawing = canvas.Canvas(str(path))
    drawing.drawString(80, 760, "Prüfprotokoll")
    drawing.save()
    return path


def test_a_reference_names_folder_and_certificate():
    reference = NssReference(Path("/data/nssdb"), "Erika # Muster")
    assert parse(reference.text()) == reference
    assert parse("/data/zertifikat.p12") is None


@needs_nss
def test_a_database_without_password_signs_at_once(tmp_path):
    make_database(tmp_path)
    reference = NssReference(tmp_path, LABEL).text()
    assert not needs_password(reference)
    assert certificate_info(reference, "").email == "erika@example.org"
    source, target = small_pdf(tmp_path / "bericht.pdf"), tmp_path / "signiert.pdf"
    assert signer_for(reference, "").sign(source, target, "Prüfung") == "Erika Muster"
    from pyhanko.pdf_utils.reader import PdfFileReader
    from pyhanko.sign.validation import validate_pdf_signature

    with target.open("rb") as stream:
        status = validate_pdf_signature(PdfFileReader(stream).embedded_signatures[0])
    assert status.intact and status.valid


@needs_nss
def test_a_protected_database_wants_its_password(tmp_path):
    make_database(tmp_path, "geheim")
    reference = NssReference(tmp_path, LABEL).text()
    assert needs_password(reference)
    with pytest.raises(SigningError, match="Falsches Passwort|Wrong password"):
        certificate_info(reference, "falsch")
    assert certificate_info(reference, "geheim").name == "Erika Muster"


def test_pinentry_hands_over_the_password_and_its_escapes(tmp_path):
    program = fake_pinentry(tmp_path, "D a%25b%0Ac")
    assert pinentry.ask("Titel", "Text mit 100 %", "Passwort:", command=program) == "a%b\nc"


def test_a_cancelled_pinentry_gives_no_password(tmp_path):
    program = fake_pinentry(tmp_path, "ERR 83886179 Operation cancelled")
    assert pinentry.ask("Titel", "Text", "Passwort:", command=program) is None


@needs_nss
def test_the_key_password_is_asked_for_until_it_opens_the_key(qtbot, tmp_path, monkeypatch):
    make_database(tmp_path, "geheim")
    reference = NssReference(tmp_path, LABEL).text()
    answers = iter(["falsch", "geheim"])
    errors = []

    def ask(title, description, prompt, error="", *_):
        errors.append(error)
        return next(answers)

    monkeypatch.setattr(pinentry, "program", lambda: "pinentry")
    monkeypatch.setattr(pinentry, "ask", ask)
    parent = QWidget()
    qtbot.addWidget(parent)
    assert key_password.password_for(parent, reference) == "geheim"
    assert errors[0] == "" and errors[1]


def test_without_pinentry_the_typed_password_is_taken(qtbot):
    parent = QWidget()
    qtbot.addWidget(parent)
    assert key_password.password_for(parent, "/irgendwo/zertifikat.p12", "getippt") == "getippt"


@needs_nss
def test_the_chooser_offers_the_certificates_of_the_folder(qtbot, tmp_path):
    from okeydocu.ui.nss_chooser import NssChooser

    make_database(tmp_path)
    chooser = NssChooser(current=NssReference(tmp_path, LABEL).text())
    qtbot.addWidget(chooser)
    assert chooser.certificates.count() == 1
    assert chooser.ok_button.isEnabled()
    assert parse(chooser.reference()) == NssReference(tmp_path, LABEL)
    chooser.folder.setText(str(tmp_path / "leer"))
    chooser._load()
    assert not chooser.ok_button.isEnabled() and chooser.hint.text()
