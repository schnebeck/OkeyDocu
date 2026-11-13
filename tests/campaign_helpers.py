# OkeyDocu - tests/campaign_helpers.py
# Shared timeline and steps of the campaign tests.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from datetime import datetime

T0 = datetime(2026, 3, 1, 10, 0, 0)


def start(service, asset_id, plan, meter):
    """These tests stage their own timeline around T0, earlier than the real start."""
    campaign = service.start(asset_id, plan, "Prüfung", "Prüfer", "simulator", meter)
    service.db.execute("UPDATE campaigns SET stored_since=NULL WHERE id=?", campaign)
    return campaign


def step_of(service, campaign_id, key):
    return next(
        s for s in service.steps(campaign_id) if service.plan_step(s).key == key
    )
