# EasyMeasurement - tests/test_seal_keys.py
# Manipulated records are turned away, checks without the key, and the key in KWallet.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import subprocess

import pytest

from easymeasurement.campaign import seal
from easymeasurement.campaign.seal import KWalletKeyStore, SealState
from easymeasurement.campaign.service import CampaignService
from easymeasurement.reporting.archive import ReportArchive, ReportError
from easymeasurement.reporting.context import build_context
from easymeasurement.reporting.template import default_template_text

from . import seal_helpers
from .seal_helpers import Key, finished, forge

# pytest looks fixtures up by name in the test module.
asset, path, sealing = seal_helpers.asset, seal_helpers.path, seal_helpers.sealing


REAL_KEY_METHOD = KWalletKeyStore.key


# Turned away -----------------------------------------------------------------


def test_report_is_refused_for_a_manipulated_record(sealing, asset):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, "UPDATE measured_values SET raw='0.10Ω'")
    with pytest.raises(ReportError, match="abgewiesen"):
        ReportArchive(sealing).generate(campaign, "Standard", default_template_text())
    assert sealing.db.query("SELECT * FROM reports") == []


def test_signing_is_refused_for_a_manipulated_record(sealing, asset):
    campaign = finished(sealing, asset)
    archive = ReportArchive(sealing)
    report = archive.generate(campaign, "Standard", default_template_text())
    forge(sealing.db.path, "UPDATE measured_values SET raw='0.10Ω'")
    with pytest.raises(ReportError, match="abgewiesen"):
        archive.sign(report, object())


def test_intact_record_gets_its_report(sealing, asset):
    report = ReportArchive(sealing).generate(
        finished(sealing, asset), "Standard", default_template_text()
    )
    assert report


def test_seal_is_part_of_the_report(sealing, asset):
    campaign = finished(sealing, asset)
    context = build_context(sealing, campaign)
    assert context["campaign"]["seal"] == sealing.campaign(campaign)["seal"]
    assert "campaign.seal" in default_template_text()


# Without the key -------------------------------------------------------------


def test_without_the_key_data_are_still_compared(path, sealing, asset, tmp_path):
    campaign = finished(sealing, asset)
    elsewhere = CampaignService(sealing.db, tmp_path / "archive", None)
    assert elsewhere.check_seal(campaign).state is SealState.UNVERIFIED
    forge(path, "UPDATE measured_values SET raw='0.10Ω'")
    assert elsewhere.check_seal(campaign).rejected


def test_another_key_rejects_the_seal(sealing, asset, tmp_path):
    campaign = finished(sealing, asset)
    elsewhere = CampaignService(sealing.db, tmp_path / "archive", Key(b"x" * 32))
    assert elsewhere.check_seal(campaign).rejected


def test_closing_without_a_reachable_key_still_seals_the_digest(sealing, asset, tmp_path):
    keyless = CampaignService(sealing.db, tmp_path / "archive", Key(None))
    campaign = finished(keyless, asset)
    row = keyless.campaign(campaign)
    assert row["seal"] and not row["seal_mac"]
    assert keyless.check_seal(campaign).state is SealState.UNVERIFIED


def test_key_is_fetched_only_once(sealing, asset):
    finished(sealing, asset)
    finished(sealing, asset)
    assert sealing.key_store.asked == 1


def test_campaign_closed_before_seals_is_named_as_such(sealing, asset):
    campaign = finished(sealing, asset)
    forge(sealing.db.path, "UPDATE campaigns SET seal='', seal_mac=''")
    assert sealing.check_seal(campaign).state is SealState.NOT_SEALED


# KWallet ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def real_key_method(monkeypatch):
    monkeypatch.setattr(KWalletKeyStore, "key", REAL_KEY_METHOD)


class Wallet:
    def __init__(self, stored=""):
        self.stored = stored
        self.calls = []

    def __call__(self, command, input=None, **kwargs):
        self.calls.append(command)
        if "-w" in command:
            self.stored = input
            return subprocess.CompletedProcess(command, 0, stdout="")
        return subprocess.CompletedProcess(command, 0 if self.stored else 1, stdout=self.stored)


def test_key_is_created_in_the_wallet_on_first_use(monkeypatch):
    wallet = Wallet()
    monkeypatch.setattr(seal.subprocess, "run", wallet)
    key = KWalletKeyStore().key()
    assert len(key) == 32
    assert wallet.stored == key.hex()


def test_stored_key_is_reused(monkeypatch):
    wallet = Wallet("ab" * 32)
    monkeypatch.setattr(seal.subprocess, "run", wallet)
    assert KWalletKeyStore().key() == bytes.fromhex("ab" * 32)
    assert not any("-w" in call for call in wallet.calls)


def test_key_goes_to_the_wallet_by_stdin_not_the_command_line(monkeypatch):
    wallet = Wallet()
    monkeypatch.setattr(seal.subprocess, "run", wallet)
    key = KWalletKeyStore().key()
    assert not any(key.hex() in " ".join(call) for call in wallet.calls)


def test_missing_wallet_means_no_key(monkeypatch):
    def missing(*args, **kwargs):
        raise FileNotFoundError("kwallet-query")

    monkeypatch.setattr(seal.subprocess, "run", missing)
    assert KWalletKeyStore().key() is None


def test_key_that_cannot_be_read_back_is_not_used(monkeypatch):
    class Forgetful(Wallet):
        def __call__(self, command, input=None, **kwargs):
            if "-w" in command:
                return subprocess.CompletedProcess(command, 0, stdout="")
            return subprocess.CompletedProcess(command, 1, stdout="")

    monkeypatch.setattr(seal.subprocess, "run", Forgetful())
    assert KWalletKeyStore().key() is None
