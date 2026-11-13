# OkeyDocu - tests/test_seal_keys.py
# Manipulated records are turned away, and checks without the key.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.campaign.seal import SealState
from okeydocu.campaign.service import CampaignService
from okeydocu.reporting.archive import ReportArchive, ReportError
from okeydocu.reporting.context import build_context
from okeydocu.reporting.template import default_template_text

from . import seal_helpers
from .seal_helpers import Key, finished, forge

# pytest looks fixtures up by name in the test module.
asset, path, sealing = seal_helpers.asset, seal_helpers.path, seal_helpers.sealing



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
