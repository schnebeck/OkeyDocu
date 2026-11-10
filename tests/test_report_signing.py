# EasyMeasurement - tests/test_report_signing.py
# Signing reports with PKCS#12 and S/MIME certificates.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import shutil
import subprocess
from datetime import datetime, timedelta, timezone

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from easymeasurement.reporting.archive import ReportArchive
from easymeasurement.reporting.sign import Pkcs12Signer, SigningError
from easymeasurement.reporting.template import default_template_text

from .report_helpers import closed_campaign


def make_certificate(path, passphrase):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Prüfer")])
    now = datetime.now(timezone.utc)
    certificate = (
        x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(
            b"test", key, certificate, None,
            serialization.BestAvailableEncryption(passphrase.encode()),
        )
    )


@pytest.mark.skipif(shutil.which("pdfsig") is None, reason="pdfsig not installed")
def test_signature_is_valid_and_leaves_the_original(service, asset_id, plan, tmp_path):
    campaign = closed_campaign(service, asset_id, plan, driver_key="profitest-prime")
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    certificate = tmp_path / "test.p12"
    make_certificate(certificate, "geheim")
    signed_id = archive.sign(report_id, Pkcs12Signer(certificate, "geheim"))
    original = service.db.one("SELECT * FROM reports WHERE id=?", report_id)
    signed = service.db.one("SELECT * FROM reports WHERE id=?", signed_id)
    assert archive.is_intact(original) and archive.is_intact(signed)
    assert "Test Prüfer" in signed["signed_by"]
    result = subprocess.run(
        ["pdfsig", str(archive.path(signed))], capture_output=True, text=True
    ).stdout
    assert "Signature is Valid" in result
    assert "ETSI.CAdES.detached" in result


def test_wrong_passphrase_is_a_clear_error(service, asset_id, plan, tmp_path):
    campaign = closed_campaign(service, asset_id, plan, driver_key="profitest-prime")
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    certificate = tmp_path / "test.p12"
    make_certificate(certificate, "geheim")
    with pytest.raises(SigningError, match="Passwort"):
        archive.sign(report_id, Pkcs12Signer(certificate, "falsch"))


# S/MIME certificates ----------------------------------------------------


def smime_identity(path, passphrase, *, legacy=False, days=30, key_usage=True):
    """A CA-issued mail certificate, built like the ones public CAs hand out."""
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Test Mail CA")])
    now = datetime.now(timezone.utc)
    ca = (
        x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name)
        .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=400)).not_valid_after(now + timedelta(days=400))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_key, hashes.SHA256())
    )
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Max Muster")])
    builder = (
        x509.CertificateBuilder().subject_name(subject).issuer_name(ca_name)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=300)).not_valid_after(now + timedelta(days=days))
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.EMAIL_PROTECTION]), False)
        .add_extension(x509.SubjectAlternativeName([x509.RFC822Name("max@example.org")]), False)
    )
    if key_usage is not None:
        builder = builder.add_extension(
            x509.KeyUsage(key_usage, False, not key_usage, False, False, False, False, False, False),
            critical=True,
        )
    certificate = builder.sign(ca_key, hashes.SHA256())
    encryption = serialization.BestAvailableEncryption(passphrase.encode())
    if legacy:  # PBES1 with 3DES and a SHA-1 MAC, the legacy PKCS#12 form
        encryption = (
            serialization.PrivateFormat.PKCS12.encryption_builder()
            .key_cert_algorithm(pkcs12.PBES.PBESv1SHA1And3KeyTripleDESCBC)
            .hmac_hash(hashes.SHA1())
            .build(passphrase.encode())
        )
    path.write_bytes(
        pkcs12.serialize_key_and_certificates(b"mail", key, certificate, [ca], encryption)
    )


@pytest.mark.parametrize("legacy", [False, True])
def test_smime_certificate_signs_a_report(service, asset_id, plan, tmp_path, legacy):
    campaign = closed_campaign(service, asset_id, plan, driver_key="profitest-prime")
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "geheim", legacy=legacy)
    signed_id = archive.sign(report_id, Pkcs12Signer(certificate, "geheim"))
    signed = service.db.one("SELECT * FROM reports WHERE id=?", signed_id)
    assert signed["signed_by"] == "Max Muster"
    result = subprocess.run(
        ["pdfsig", str(archive.path(signed))], capture_output=True, text=True
    ).stdout
    assert "Signature is Valid" in result


def test_certificate_details_are_shown_before_signing(tmp_path):
    from easymeasurement.reporting.sign import inspect_certificate

    path = tmp_path / "mail.p12"
    smime_identity(path, "geheim")
    info = inspect_certificate(path, "geheim")
    assert (info.name, info.email, info.issuer) == ("Max Muster", "max@example.org", "Test Mail CA")
    assert info.email_only and info.can_sign and not info.expired


def test_expired_certificate_is_refused(tmp_path):
    path = tmp_path / "mail.p12"
    smime_identity(path, "geheim", days=-1)
    with pytest.raises(SigningError, match="abgelaufen"):
        Pkcs12Signer(path, "geheim").sign(tmp_path / "a.pdf", tmp_path / "b.pdf", "x")


def test_encryption_only_certificate_is_refused(tmp_path):
    path = tmp_path / "mail.p12"
    smime_identity(path, "geheim", key_usage=False)
    with pytest.raises(SigningError, match="nicht zum Signieren"):
        Pkcs12Signer(path, "geheim").sign(tmp_path / "a.pdf", tmp_path / "b.pdf", "x")


def test_nothing_of_the_certificate_reaches_the_database(service, asset_id, plan, tmp_path):
    campaign = closed_campaign(service, asset_id, plan, driver_key="profitest-prime")
    archive = ReportArchive(service)
    report_id = archive.generate(campaign, "Standard", default_template_text())
    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "streng-geheim")
    archive.sign(report_id, Pkcs12Signer(certificate, "streng-geheim"))
    dump = "\n".join(service.db.connection.iterdump())
    assert "streng-geheim" not in dump and "mail.p12" not in dump


def test_signing_remembers_the_path_but_never_the_passphrase(
    service, asset_id, plan, tmp_path, qtbot, monkeypatch
):
    from easymeasurement.paths import data_dir
    from easymeasurement.ui import report_signing
    from easymeasurement.ui import reports as reports_ui
    from easymeasurement.ui.common import AppContext

    campaign = closed_campaign(service, asset_id, plan, driver_key="profitest-prime")
    archive = ReportArchive(service)
    archive.generate(campaign, "Standard", default_template_text())
    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "streng-geheim")

    page = reports_ui.ReportsPage(AppContext(service.db, service, archive))
    qtbot.addWidget(page)
    page.table.setCurrentCell(0, 0)
    owners = []

    def fill(overlay):
        overlay.certificate.path.setText(str(certificate))
        overlay.certificate.passphrase.setText("streng-geheim")
        overlay.certificate._show_owner()
        owners.append(overlay.certificate.info.text())
        return True

    monkeypatch.setattr(report_signing.SignOverlay, "exec", fill)
    page._sign()

    assert page.table.rowCount() == 2
    assert "Max Muster" in owners[0] and "S/MIME" in owners[0]
    report_signing.settings().sync()
    stored = (data_dir() / "settings.ini").read_text()
    assert "mail.p12" in stored and "streng-geheim" not in stored
    assert report_signing.CertificateFields().path.text() == str(certificate)


def test_a_wrong_password_keeps_the_overlay_open(tmp_path, qtbot):
    from easymeasurement.ui.report_signing import SignOverlay

    certificate = tmp_path / "mail.p12"
    smime_identity(certificate, "streng-geheim")
    overlay = SignOverlay(certificate=str(certificate))
    qtbot.addWidget(overlay)
    overlay.certificate.passphrase.setText("falsch")
    overlay.accept()
    assert not overlay.accepted
    assert "Passwort" in overlay.hint.text()
