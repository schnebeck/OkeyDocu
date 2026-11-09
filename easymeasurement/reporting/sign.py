# EasyMeasurement - easymeasurement/reporting/sign.py
# PDF signatures with an X.509 certificate, including S/MIME certificates.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_DOCUMENT_SIGNING = x509.ObjectIdentifier("1.3.6.1.5.5.7.3.36")


class SigningError(Exception):
    pass


class PdfSigner(Protocol):
    def sign(self, source: Path, target: Path, reason: str) -> str:
        """Write a signed copy of source to target and return the signer's name."""


@dataclass(frozen=True)
class CertificateInfo:
    name: str
    email: str
    issuer: str
    valid_until: datetime
    expired: bool
    can_sign: bool
    email_only: bool  # issued for mail (S/MIME), not explicitly for documents


def _attribute(name: x509.Name, oid) -> str:
    found = name.get_attributes_for_oid(oid)
    return str(found[0].value) if found else ""


def _extension(certificate: x509.Certificate, kind):
    try:
        return certificate.extensions.get_extension_for_class(kind).value
    except x509.ExtensionNotFound:
        return None


def inspect_certificate(path: Path, passphrase: str) -> CertificateInfo:
    """Read a PKCS#12 file without keeping anything from it."""
    try:
        _, certificate, _ = pkcs12.load_key_and_certificates(
            path.read_bytes(), passphrase.encode() or None
        )
    except (ValueError, OSError) as err:
        raise SigningError("Zertifikat nicht lesbar oder Passwort falsch.") from err
    if certificate is None:
        raise SigningError("Die Datei enthält kein Zertifikat.")
    alternative = _extension(certificate, x509.SubjectAlternativeName)
    addresses = alternative.get_values_for_type(x509.RFC822Name) if alternative else []
    usage = _extension(certificate, x509.KeyUsage)
    extended = _extension(certificate, x509.ExtendedKeyUsage)
    purposes = list(extended) if extended else []
    until = certificate.not_valid_after_utc
    return CertificateInfo(
        name=_attribute(certificate.subject, NameOID.COMMON_NAME) or certificate.subject.rfc4514_string(),
        email=addresses[0] if addresses else _attribute(certificate.subject, NameOID.EMAIL_ADDRESS),
        issuer=_attribute(certificate.issuer, NameOID.COMMON_NAME),
        valid_until=until,
        expired=until < datetime.now(timezone.utc),
        can_sign=usage is None or usage.digital_signature or usage.content_commitment,
        email_only=ExtendedKeyUsageOID.EMAIL_PROTECTION in purposes
        and _DOCUMENT_SIGNING not in purposes,
    )


class Pkcs12Signer:
    """Signs with a certificate from a PKCS#12 file, for example an exported S/MIME identity.

    The file stays where it is. The passphrase is used for this one call and is
    not stored anywhere.
    """

    def __init__(self, certificate: Path, passphrase: str):
        self.certificate = certificate
        self.passphrase = passphrase

    def sign(self, source: Path, target: Path, reason: str) -> str:
        from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
        from pyhanko.sign import fields, signers

        info = inspect_certificate(self.certificate, self.passphrase)
        if info.expired:
            raise SigningError(f"Das Zertifikat ist seit {info.valid_until:%d.%m.%Y} abgelaufen.")
        if not info.can_sign:
            raise SigningError("Dieses Zertifikat ist nicht zum Signieren ausgestellt.")
        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=str(self.certificate), passphrase=self.passphrase.encode() or None
        )
        if signer is None:
            raise SigningError("Zertifikat nicht lesbar oder Passwort falsch.")
        metadata = signers.PdfSignatureMetadata(
            field_name="Signatur",
            reason=reason,
            md_algorithm="sha256",
            subfilter=fields.SigSeedSubFilter.PADES,
        )
        with source.open("rb") as stream, target.open("wb") as output:
            writer = IncrementalPdfFileWriter(stream)
            signers.sign_pdf(writer, metadata, signer=signer, output=output)
        return info.name
