# OkeyDocu - tests/nss_helpers.py
# A throwaway NSS database with a self-made certificate and its key, for signing tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import datetime
import os

from asn1crypto.core import Integer
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

LABEL = "Erika Muster - Test CA"


def _big(value: int) -> bytes:
    return value.to_bytes((value.bit_length() + 7) // 8, "big")


def _certificate(key, days: int = 30):
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Erika Muster"),
                      x509.NameAttribute(NameOID.EMAIL_ADDRESS, "erika@example.org")])
    now = datetime.datetime.now(datetime.timezone.utc)
    return (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=days))
            .sign(key, hashes.SHA256()))


def make_database(folder, password: str = "") -> None:
    """A database in `folder` holding one certificate with its key; with `password`, the key
    is only reached after logging in."""
    import pkcs11
    from pkcs11 import Attribute, ObjectClass

    from okeydocu.reporting import nss

    os.environ["NSS_LIB_PARAMS"] = (f"configdir='sql:{folder}' certPrefix='' keyPrefix=''"
                                    " secmod='secmod.db' flags=")
    if "lib" in nss._opened:
        nss._opened["lib"].reinitialize()
    else:
        nss._opened["lib"] = pkcs11.lib(nss._module_path())
    nss._opened["folder"] = None  # opened read-only again on the next use
    token = next(slot.get_token() for slot in nss._opened["lib"].get_slots()
                 if "Private Key" in slot.slot_description)
    with token.open(rw=True, so_pin="") as session:
        session.init_pin(password)
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    certificate = _certificate(key)
    numbers, kid = key.private_numbers(), b"\x07"
    with token.open(rw=True, user_pin=password or None) as session:
        session.create_object({
            Attribute.CLASS: ObjectClass.PRIVATE_KEY, Attribute.KEY_TYPE: pkcs11.KeyType.RSA,
            Attribute.TOKEN: True, Attribute.PRIVATE: True, Attribute.SENSITIVE: True,
            Attribute.SIGN: True, Attribute.LABEL: LABEL, Attribute.ID: kid,
            Attribute.MODULUS: _big(numbers.public_numbers.n),
            Attribute.PUBLIC_EXPONENT: _big(numbers.public_numbers.e),
            Attribute.PRIVATE_EXPONENT: _big(numbers.d), Attribute.PRIME_1: _big(numbers.p),
            Attribute.PRIME_2: _big(numbers.q), Attribute.EXPONENT_1: _big(numbers.dmp1),
            Attribute.EXPONENT_2: _big(numbers.dmq1), Attribute.COEFFICIENT: _big(numbers.iqmp)})
        session.create_object({
            Attribute.CLASS: ObjectClass.CERTIFICATE,
            Attribute.CERTIFICATE_TYPE: pkcs11.CertificateType.X_509,
            Attribute.TOKEN: True, Attribute.LABEL: LABEL, Attribute.ID: kid,
            Attribute.SUBJECT: certificate.subject.public_bytes(),
            Attribute.ISSUER: certificate.issuer.public_bytes(),
            Attribute.SERIAL_NUMBER: Integer(certificate.serial_number).dump(),
            Attribute.VALUE: certificate.public_bytes(serialization.Encoding.DER)})
