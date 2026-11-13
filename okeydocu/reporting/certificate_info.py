# OkeyDocu - okeydocu/reporting/certificate_info.py
# What a signing certificate says about its owner, its issuer and what it may sign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from cryptography import x509
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

_DOCUMENT_SIGNING = x509.ObjectIdentifier("1.3.6.1.5.5.7.3.36")


class SigningError(Exception):
    pass


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


def describe_certificate(certificate: x509.Certificate) -> CertificateInfo:
    alternative = _extension(certificate, x509.SubjectAlternativeName)
    addresses = alternative.get_values_for_type(x509.RFC822Name) if alternative else []
    usage = _extension(certificate, x509.KeyUsage)
    extended = _extension(certificate, x509.ExtendedKeyUsage)
    purposes = list(extended) if extended else []
    until = certificate.not_valid_after_utc
    return CertificateInfo(
        name=(_attribute(certificate.subject, NameOID.COMMON_NAME)
              or certificate.subject.rfc4514_string()),
        email=addresses[0] if addresses else _attribute(certificate.subject,
                                                         NameOID.EMAIL_ADDRESS),
        issuer=_attribute(certificate.issuer, NameOID.COMMON_NAME),
        valid_until=until,
        expired=until < datetime.now(timezone.utc),
        can_sign=usage is None or usage.digital_signature or usage.content_commitment,
        email_only=ExtendedKeyUsageOID.EMAIL_PROTECTION in purposes
        and _DOCUMENT_SIGNING not in purposes,
    )
