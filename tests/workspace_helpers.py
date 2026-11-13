# OkeyDocu - tests/workspace_helpers.py
# Shared steps of the workspace tests: an asset and a started campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from okeydocu.devices import FoundInstrument
from okeydocu.ui.campaign_dialog import CampaignDialog


def with_asset(window, app):
    app.db.add_asset(app.db.add_customer("Muster AG"), "installation", "Halle 1")
    app.db.add_user("A. Prüfer")
    window.campaign.refresh()


def start(window, monkeypatch, plan="Ohne Plan", simulated=False):
    if simulated:
        monkeypatch.setattr(
            "okeydocu.ui.campaign_dialog.find_instruments",
            lambda: [FoundInstrument("simulator", "Simulator (Zufallswerte)")],
        )

    def fill(dialog):
        dialog.plan.setCurrentIndex(dialog.plan.findText(plan))
        dialog.title.setText("Prüfung Halle")
        if simulated:
            dialog.source.setCurrentIndex(dialog.source.findText("Simulator (Zufallswerte)"))
        return 1

    monkeypatch.setattr(CampaignDialog, "exec", fill)
    window.campaign.home.start_button.click()


def plan_title(window):
    return window.guided.plans[0].label  # as the start dialog lists it
