# EasyMeasurement - tests/seal_helpers.py
# Fixtures of the seal tests: a sealing service, a finished campaign and forgery.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import sqlite3

import pytest

from easymeasurement.campaign.service import CampaignService
from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.store import Database


class Key:
    def __init__(self, key=b"k" * 32):
        self.value = key
        self.asked = 0

    def key(self):
        self.asked += 1
        return self.value


@pytest.fixture
def path(tmp_path):
    return tmp_path / "data.sqlite"


@pytest.fixture
def sealing(path, tmp_path):
    db = Database(path)
    service = CampaignService(db, tmp_path / "archive", Key())
    yield service
    db.close()


@pytest.fixture
def asset(sealing):
    return sealing.db.add_asset(sealing.db.add_customer("Muster AG"), "machine", "Presse")


def finished(service, asset, title="Prüfung"):
    campaign = service.create(asset, title, "Prüfer")
    service.add_measurement(
        campaign, "rlo", [ResultValue("rlo", "RLO", Quantity.parse("0.21Ω"), Verdict.PASSED)],
        verdict=Verdict.PASSED, comment="ok",
    )
    service.close(campaign)
    return campaign


def forge(path, *statements):
    """What someone with the file and sqlite3 can do: remove the rules, then write."""
    connection = sqlite3.connect(path)
    triggers = [row[0] for row in connection.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger'"
    )]
    for trigger in triggers:
        connection.execute(f"DROP TRIGGER {trigger}")
    for statement in statements:
        connection.execute(statement)
    connection.commit()
    connection.close()
