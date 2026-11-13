# OkeyDocu - okeydocu/reporting/nss.py
# Signing straight from an NSS database, the store of Firefox, Chromium and others.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""NSS's own PKCS#11 module, the softoken, opens one database folder, always read-only. The
folder is handed over in NSS_LIB_PARAMS, which the softoken reads when it is initialised
without arguments, as python-pkcs11 does; choosing another folder initialises it anew. The
key never leaves the database: pyHanko asks the token to sign."""

from __future__ import annotations

import ctypes.util
import os
from dataclasses import dataclass
from pathlib import Path

from cryptography import x509

from ..l10n import day, tr
from .certificate_info import CertificateInfo, SigningError, describe_certificate

PREFIX = "nss:"
DEFAULT_FOLDER = Path.home() / ".pki" / "nssdb"
_SOFTOKEN = ("/usr/lib/x86_64-linux-gnu/libsoftokn3.so", "/usr/lib64/libsoftokn3.so",
             "/usr/lib/libsoftokn3.so")
_KEY_SLOT = "Private Key"  # the slot of the database, beside the one of plain crypto
_opened: dict = {}  # the module once loaded, and the folder it was initialised for


@dataclass(frozen=True)
class NssReference:
    folder: Path
    label: str  # the certificate's nickname in the database

    def text(self) -> str:
        return f"{PREFIX}{self.folder}#{self.label}"


def parse(reference: str) -> NssReference | None:
    """`nss:<folder>#<nickname>`; None for anything else, such as the path of a file."""
    if not reference.startswith(PREFIX) or "#" not in reference:
        return None
    folder, _, label = reference[len(PREFIX):].partition("#")
    return NssReference(Path(folder), label)


def _module_path() -> str:
    found = next((path for path in _SOFTOKEN if os.path.exists(path)), None)
    found = found or ctypes.util.find_library("softokn3")
    if not found:
        raise SigningError(tr("NSS is not installed on this computer."))
    return found


def _token(folder: Path):
    try:
        import pkcs11
    except ImportError as err:
        raise SigningError(tr("Signing from an NSS database needs python-pkcs11.")) from err
    if not (folder / "cert9.db").exists():
        raise SigningError(tr("No NSS database in {folder}.", folder=str(folder)))
    os.environ["NSS_LIB_PARAMS"] = (f"configdir='sql:{folder}' certPrefix='' keyPrefix=''"
                                    " secmod='secmod.db' flags=readOnly")
    if "lib" not in _opened:
        _opened["lib"] = pkcs11.lib(_module_path())
    elif _opened.get("folder") != folder:
        _opened["lib"].reinitialize()
    _opened["folder"] = folder
    slots = _opened["lib"].get_slots()
    return next(slot.get_token() for slot in slots if _KEY_SLOT in slot.slot_description)


def needs_password(folder: Path) -> bool:
    import pkcs11

    return bool(_token(folder).flags & pkcs11.TokenFlag.LOGIN_REQUIRED)


def _session(folder: Path, password: str):
    token = _token(folder)
    import pkcs11

    try:
        return token.open(user_pin=password) if needs_password(folder) else token.open()
    except pkcs11.PinIncorrect as err:
        raise SigningError(tr("Wrong password for the NSS database.")) from err


def identities(folder: Path, password: str = "") -> list[tuple[str, CertificateInfo]]:
    """Every certificate of the database that has its key there, by nickname. Without the
    password of a protected database, keys cannot be seen: then every certificate is
    listed."""
    from pkcs11 import Attribute, ObjectClass

    found = []
    with _session(folder, password) if password or not needs_password(folder) \
            else _token(folder).open() as session:
        certificates = list(session.get_objects({Attribute.CLASS: ObjectClass.CERTIFICATE}))
        for obj in certificates:
            certificate = x509.load_der_x509_certificate(obj[Attribute.VALUE])
            keys = list(session.get_objects({Attribute.CLASS: ObjectClass.PRIVATE_KEY,
                                             Attribute.ID: obj[Attribute.ID]}))
            if keys or needs_password(folder) and not password:
                found.append((obj[Attribute.LABEL], describe_certificate(certificate)))
    return found


def inspect(reference: NssReference, password: str) -> CertificateInfo:
    for label, info in identities(reference.folder, password):
        if label == reference.label:
            return info
    raise SigningError(tr("The certificate is not in the NSS database, or its key is missing."))


class NssSigner:
    """Signs with a certificate whose key stays in an NSS database."""

    def __init__(self, reference: NssReference, password: str):
        self.reference = reference
        self.password = password

    def sign(self, source: Path, target: Path, reason: str) -> str:
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import fields, signers
        from pyhanko.sign.pkcs11 import PKCS11Signer

        info = inspect(self.reference, self.password)
        if info.expired:
            raise SigningError(tr("The certificate expired on {day}.", day=day(info.valid_until)))
        if not info.can_sign:
            raise SigningError(tr("This certificate is not issued for signing."))
        with _session(self.reference.folder, self.password) as session:
            signer = PKCS11Signer(session, cert_label=self.reference.label,
                                  key_label=self.reference.label)
            metadata = signers.PdfSignatureMetadata(
                field_name="Signatur", reason=reason, md_algorithm="sha256",
                subfilter=fields.SigSeedSubFilter.PADES)
            with source.open("rb") as pdf, target.open("wb") as output:
                signers.sign_pdf(IncrementalPdfFileWriter(pdf), metadata, signer=signer,
                                 output=output)
        return info.name
