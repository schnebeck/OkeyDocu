# OkeyDocu - tests/test_value_language.py
# A value of a choice list is stored in one language and shown in the one of the reader.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest

from okeydocu.l10n import speaking
from okeydocu.reporting.levels import asset_features


@pytest.fixture
def machine(app):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    app.db.set_asset_features(machine, {"line_conductors": "1", "n_conductor": "with N"})
    return machine


def test_a_list_tells_its_values_in_the_language_and_leaves_other_text(app):
    chosen = next(found for found in app.db.choice_lists().values()
                  if "with N" in found.offered)
    assert chosen.shown("with N") == "mit N"
    assert chosen.shown("mit Sternpunkt") == "mit Sternpunkt"
    with speaking("en"):
        assert chosen.shown("with N") == "with N"


def test_the_side_panel_shows_a_list_value_in_the_language(window, app, machine):
    page = window.campaign
    page.refresh()
    page.show_campaign(app.service.create(machine, "Prüfung", "Prüfer"))
    texts = page.place.detail_texts()
    assert "mit N" in texts and "with N" not in texts


def test_the_report_card_follows_the_language_of_the_report(app, machine):
    asset = app.db.asset(machine)
    assert ("Neutralleiter", "mit N") in asset_features(app.db, asset)
    with speaking("en"):
        assert "with N" in [value for _, value in asset_features(app.db, asset)]

