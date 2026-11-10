# EasyMeasurement - tests/test_workspace_by_hand.py
# Values typed in by hand during a campaign.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from easymeasurement.ui.measurement_overlays import MeasurementOverlay


def test_a_value_typed_in_lands_where_the_tree_points(window, app, monkeypatch):
    customer = app.db.add_customer("Muster AG")
    machine = app.db.add_asset(customer, "machine", "Presse")
    cabinet = app.db.add_asset(customer, "measuring_point", "Schrank", parent_id=machine)
    campaign = app.service.create(machine, "Prüfung", "Prüfer")
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    page.structure.select(cabinet)
    seen = []
    monkeypatch.setattr(MeasurementOverlay, "exec",
                        lambda overlay: seen.append(overlay.location.text()) or 1)
    page.values.manual_action.trigger()
    assert seen == ["Presse / Schrank"]
    row = app.db.one("SELECT asset_id FROM measurements WHERE campaign_id=?", campaign)
    assert row["asset_id"] == cabinet
    assert page.values.table.rowCount() == 1


def test_the_first_value_is_named_after_the_function(qtbot):
    overlay = MeasurementOverlay()
    qtbot.addWidget(overlay)
    overlay.function.setCurrentIndex(overlay.function.findData("rlo"))
    assert overlay.table.item(0, 0).text() == "RLO"
    overlay.function.setCurrentIndex(overlay.function.findData("riso"))
    assert overlay.table.item(0, 0).text() == "RISO"
