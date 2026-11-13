# OkeyDocu - okeydocu/reporting/sign.py
# PDF signatures with an X.509 certificate, including S/MIME certificates.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from cryptography.hazmat.primitives.serialization import pkcs12

from ..l10n import day, tr
from .certificate_info import CertificateInfo, SigningError, describe_certificate
from .nss import NssSigner, parse
from .nss import inspect as inspect_nss
from .nss import needs_password as nss_needs_password

__all__ = ["CertificateInfo", "SigningError", "PdfSigner", "Pkcs12Signer", "inspect_certificate",
           "certificate_info", "signer_for", "needs_password"]


class PdfSigner(Protocol):
    def sign(self, source: Path, target: Path, reason: str) -> str:
        """Write a signed copy of source to target and return the signer's name."""


def inspect_certificate(path: Path, passphrase: str) -> CertificateInfo:
    """Read a PKCS#12 file without keeping anything from it."""
    try:
        _, certificate, _ = pkcs12.load_key_and_certificates(
            path.read_bytes(), passphrase.encode() or None
        )
    except (ValueError, OSError) as err:
        raise SigningError(tr("Certificate not readable or wrong password.")) from err
    if certificate is None:
        raise SigningError(tr("The file contains no certificate."))
    return describe_certificate(certificate)


def certificate_info(reference: str, password: str) -> CertificateInfo:
    """A certificate named by the path of a PKCS#12 file or by an NSS reference."""
    nss = parse(reference)
    if nss is not None:
        return inspect_nss(nss, password)
    return inspect_certificate(Path(reference), password)


def needs_password(reference: str) -> bool:
    """Whether the key can only be reached with a password."""
    nss = parse(reference)
    if nss is not None:
        return nss_needs_password(nss.folder)
    try:
        inspect_certificate(Path(reference), "")
    except SigningError:
        return True
    return False


def signer_for(reference: str, password: str) -> PdfSigner:
    nss = parse(reference)
    return NssSigner(nss, password) if nss is not None else Pkcs12Signer(Path(reference),
                                                                         password)


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
            raise SigningError(tr("The certificate expired on {day}.", day=day(info.valid_until)))
        if not info.can_sign:
            raise SigningError(tr("This certificate is not issued for signing."))
        signer = signers.SimpleSigner.load_pkcs12(
            pfx_file=str(self.certificate), passphrase=self.passphrase.encode() or None
        )
        if signer is None:
            raise SigningError(tr("Certificate not readable or wrong password."))
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
