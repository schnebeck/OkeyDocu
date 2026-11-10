# EasyMeasurement - tests/test_workspace_values.py
# The data table: many values, what all rows share, and conductors.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import time
from datetime import datetime

from easymeasurement.model import Quantity, ResultValue, Verdict


# Many values -----------------------------------------------------------------


def many_values(app, count=300):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    long_text = "Ist die Anlage entsprechend den Anforderungen errichtet? " * 6
    for number in range(count):
        app.service.add_measurement(
            campaign, "other",
            [ResultValue("question", "Prüffrage", Quantity(raw=f"{number} {long_text}"))],
        )
    app.service.close(campaign)
    return campaign


def test_large_campaign_opens_at_once_on_a_visible_table(window, app):
    """Filling must not measure the table after every single cell."""
    campaign = many_values(app)
    window.campaign.refresh()
    started = time.monotonic()
    window.campaign.list.tree.setCurrentItem(window.campaign.list.items[campaign])
    assert time.monotonic() - started < 3
    assert window.campaign.values.table.rowCount() == 300


def test_long_texts_do_not_push_the_verdict_out_of_the_table(window, app):
    campaign = many_values(app, 3)
    window.campaign.refresh()
    window.resize(1360, 860)
    window.campaign.show_campaign(campaign)
    table = window.campaign.values.table
    assert table.horizontalHeader().length() <= table.viewport().width()


def test_long_campaign_names_do_not_widen_the_window(window, app):
    before = window.minimumSizeHint().width()
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    app.service.create(asset, "Eine wirklich sehr lange Bezeichnung " * 5, "Prüfer")
    window.campaign.refresh()
    window.measurements.reload_choices()
    assert window.minimumSizeHint().width() <= before


# What all rows share ---------------------------------------------------------


def two_places(app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    moment = datetime(2026, 10, 22, 10, 0, 0)
    for place, function in (("Presse / Schrank / F1", "rlo"), ("Presse / Schrank / F2", "rlo")):
        app.service.add_measurement(
            campaign, function, [ResultValue("rlo", "RLO", Quantity.parse("0.21Ω"))], moment,
            Verdict.PASSED, location=place,
        )
    return asset, campaign


def data_page(window, app):
    page = window.measurements
    window.open_page(page)
    page.reload_choices()
    page.refresh()
    return page


def test_what_all_rows_share_moves_to_the_head(window, app):
    two_places(app)
    page = data_page(window, app)
    text = page.common.text()
    for part in ("Muster AG", "Presse", "Prüfung", "RLO", "bestanden", "22.10.2026"):
        assert part in text
    for column in (1, 2, 3, 5, 8):
        assert page.table.isColumnHidden(column)


def test_what_differs_stays_in_the_table(window, app):
    two_places(app)
    page = data_page(window, app)
    assert not page.table.isColumnHidden(4)
    assert not page.table.isColumnHidden(0)
    assert not page.table.isColumnHidden(6)


def test_place_does_not_repeat_the_installation(window, app):
    two_places(app)
    page = data_page(window, app)
    assert page.table.item(0, 4).text() in ("F1", "F2")


def test_shared_start_of_the_path_moves_to_the_head(window, app):
    two_places(app)
    page = data_page(window, app)
    assert "Bereich: <b>Schrank</b>" in page.common.text()


def test_paths_of_different_depth_keep_their_last_part(window, app):
    asset, campaign = two_places(app)
    app.service.add_measurement(campaign, "rlo", [], location="Presse / Schrank")
    page = data_page(window, app)
    places = {page.table.item(row, 4).text() for row in range(3)}
    assert places == {"Schrank", "Schrank / F1", "Schrank / F2"}


def test_one_day_shows_only_the_time_in_the_table(window, app):
    two_places(app)
    page = data_page(window, app)
    assert page.table.item(0, 0).text() == "10:00:00"


def test_rows_that_differ_bring_their_column_back(window, app):
    asset, campaign = two_places(app)
    app.service.add_measurement(campaign, "riso", [], datetime(2026, 10, 23, 9, 0), Verdict.FAILED)
    page = data_page(window, app)
    assert not page.table.isColumnHidden(5)
    assert not page.table.isColumnHidden(8)
    assert "23.10.2026" in page.table.item(2, 0).text()
    assert "Datum" not in page.common.text()


def test_a_single_row_keeps_all_its_columns(window, app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    app.service.add_measurement(app.service.create(asset, "T", "P"), "rlo", [])
    page = data_page(window, app)
    assert not page.table.isColumnHidden(1)
    assert page.common.isHidden()


def test_empty_column_disappears_without_a_mention(window, app):
    two_places(app)
    page = data_page(window, app)
    assert page.table.isColumnHidden(7)
    assert "Fotos" not in page.common.text()


def test_names_with_markup_are_shown_as_text(window, app):
    asset = app.db.add_asset(app.db.add_customer("<b>A&B</b>"), "machine", "Presse")
    campaign = app.service.create(asset, "T", "P")
    app.service.add_measurement(campaign, "rlo", [])
    app.service.add_measurement(campaign, "rlo", [])
    page = data_page(window, app)
    assert "&lt;b&gt;A&amp;B" in page.common.text()


def test_measurements_run_from_oldest_to_newest(window, app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "T", "P")
    for hour in (12, 9, 15):
        app.service.add_measurement(campaign, "rlo", [], datetime(2026, 10, 22, hour, 0))
    page = data_page(window, app)
    assert [page.table.item(row, 0).text() for row in range(3)] == [
        "09:00:00", "12:00:00", "15:00:00",
    ]


# Which conductors ------------------------------------------------------------


def voltages(app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "T", "P")
    for conductor, reading in (("L1-PE", "225V"), ("L1-L2", "390V")):
        measurement = app.service.add_measurement(
            campaign, "u", [ResultValue("u", "U", Quantity.parse(reading))],
            datetime(2026, 10, 22, 11, 0),
        )
        app.db.execute(
            "UPDATE measurements SET parameters_json=? WHERE id=?",
            f'[{{"key": "NETZ - Leiter", "value": "{conductor}"}}]', measurement,
        )
    return campaign


def test_conductor_stands_with_the_reading(window, app):
    voltages(app)
    page = data_page(window, app)
    texts = {page.table.item(row, 6).text() for row in range(2)}
    assert texts == {"L1-PE:  U 225V", "L1-L2:  U 390V"}


def test_measurement_without_a_conductor_shows_only_its_values(window, app):
    two_places(app)
    page = data_page(window, app)
    assert page.table.item(0, 6).text() == "RLO 0.21Ω"


def test_running_campaign_shows_the_conductor(window, app):
    campaign = voltages(app)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    assert page.values.table.item(0, 6).text().startswith(("L1-PE:", "L1-L2:"))


def test_rotating_field_reads_in_german_and_can_be_found(window, app):
    asset = app.db.add_asset(app.db.add_customer("Muster AG"), "machine", "Presse")
    campaign = app.service.create(asset, "T", "P")
    app.service.add_measurement(
        campaign, "u3", [ResultValue("rotation", "Drehfeld", Quantity(raw="right"))]
    )
    page = data_page(window, app)
    assert page.table.item(0, 6).text() == "Drehfeld rechts"
    page.text.setText("rechts")
    page._debounce.stop()
    page.refresh()
    assert page.table.rowCount() == 1


def test_choosing_a_part_of_the_installation_narrows_the_table(window, app):
    customer = app.db.add_customer("Muster AG")
    hall = app.db.add_asset(customer, "installation", "Halle")
    cabinet = app.db.add_asset(customer, "distribution_board", "Schrank", parent_id=hall)
    circuit = app.db.add_asset(customer, "circuit", "F1", parent_id=cabinet)
    campaign = app.service.create(hall, "T", "P")
    here = app.service.add_measurement(campaign, "rlo", [])
    app.service.add_measurement(campaign, "rlo", [])
    app.db.execute("UPDATE measurements SET asset_id=? WHERE id=?", circuit, here)
    page = window.campaign
    page.refresh()
    page.show_campaign(campaign)
    assert page.values.table.rowCount() == 2
    tree = page.structure
    tree.select(cabinet)
    assert page.values.table.rowCount() == 1  # the cabinet holds the circuit
    tree.select(hall)
    assert page.values.table.rowCount() == 2
