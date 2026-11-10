# EasyMeasurement - tests/test_ui.py
# The window against a real database, offscreen.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from easymeasurement.__main__ import build_context
from easymeasurement.model import Quantity, ResultValue, Verdict
from easymeasurement.ui.main_window import MainWindow


def value(text, verdict=Verdict.PASSED):
    return ResultValue("riso", "RISO", Quantity.parse(text), verdict, ">1.00MΩ")


@pytest.fixture
def window(qtbot):
    app = build_context()
    customer = app.db.add_customer("Müller Maschinenbau")
    other = app.db.add_customer("Nordwerk AG")
    press = app.db.add_asset(customer, "machine", "Presse 7")
    pump = app.db.add_asset(other, "device", "Pumpe")
    first = app.service.create(press, "Wiederholung", "Prüfer")
    second = app.service.create(pump, "Erstprüfung", "Prüfer")
    moment = datetime(2026, 3, 1, 10, 0)
    app.service.add_measurement(first, "riso", [value("2.05MΩ")], moment, Verdict.PASSED)
    app.service.add_measurement(
        first, "riso", [value("500kΩ", Verdict.FAILED)], moment, Verdict.FAILED
    )
    app.service.add_measurement(second, "riso", [value("9.00MΩ")], moment, Verdict.PASSED)
    main = MainWindow(app)
    main.app = app
    main.first = first
    main.measurements.reload_choices()
    main.measurements.refresh()
    qtbot.addWidget(main)
    yield main
    app.db.close()


def rows(window):
    return window.measurements.table.rowCount()


def test_all_measurements_are_listed(window):
    assert rows(window) == 3
    assert window.measurements.count.text() == "3 Messungen"


def test_text_filter(window, qtbot):
    window.measurements.text.setText("müller")
    qtbot.waitUntil(lambda: rows(window) == 2)


def test_customer_filter_narrows_the_asset_list(window):
    page = window.measurements
    page.customer.setCurrentIndex(page.customer.findText("Nordwerk AG"))
    assert rows(window) == 1
    assert [page.asset.itemText(i) for i in range(page.asset.count())] == ["Alle Anlagen", "Pumpe"]


def test_verdict_filter(window):
    page = window.measurements
    page.verdict.setCurrentIndex(page.verdict.findData("failed"))
    assert rows(window) == 1


def test_value_range_filter_understands_units(window, qtbot):
    page = window.measurements
    page.value_max.setText("1MΩ")
    qtbot.waitUntil(lambda: rows(window) == 1)
    assert "500kΩ" in page.table.item(0, 6).text()


def test_value_range_ignores_other_units(window, qtbot):
    app = window.app
    app.service.add_measurement(
        window.first, "u", [ResultValue("u", "U", Quantity.parse("230V"))], datetime(2026, 3, 1)
    )
    page = window.measurements
    page.refresh()
    assert rows(window) == 4
    page.value_max.setText("1MΩ")
    qtbot.waitUntil(lambda: rows(window) == 1)


def test_selecting_a_row_shows_its_values(window):
    page = window.measurements
    page.table.setCurrentCell(0, 0)
    assert page.values.rowCount() == 1
    assert page.edit_measurement.isEnabled()
    window.campaign.show_campaign(window.first)
    assert window.campaign.values.manual_action.isEnabled()
    assert not window.campaign.fetch_action.isEnabled()  # manual campaign has no instrument


def test_template_preview_renders_each_case(window):
    page = window.templates
    for index in range(3):
        page.count.setCurrentIndex(index)
        assert page.message.text() == ""
        assert page.document.pageCount() >= 1


def test_template_preview_is_really_a_rendered_page(window):
    from PySide6.QtCore import QSize

    page = window.templates
    image = page.document.render(0, QSize(300, 420))
    colours = {image.pixelColor(x, y).lightness() for x in range(0, 300, 3) for y in range(0, 420, 3)}
    assert len(colours) > 3  # text on paper, not a blank page


def test_values_column_is_readable(window):
    page = window.measurements
    window.resize(1360, 820)
    window.show()
    window.open_page(page)
    QApplication.processEvents()  # the stretching column gets its width from the layout
    assert page.table.columnWidth(6) >= page.table.fontMetrics().horizontalAdvance("RISO 2.05MΩ")


def test_broken_template_is_reported_not_saved(window, monkeypatch):
    page = window.templates
    monkeypatch.setattr("easymeasurement.ui.template_document.show_error", lambda *_: None)
    before = window.app.db.templates()[0]["body"]
    page.modes.setCurrentWidget(page.editor)
    page.editor.setPlainText("blocks:\n  - type: magic\n")
    page._save()
    assert "Unbekannter Block" in page.message.text()
    assert window.app.db.templates()[0]["body"] == before


def test_master_data_shows_customers_and_their_structure(window):
    page = window.master_data
    assert page.customers.count() == 2
    page.customers.setCurrentRow(0)
    assert page.tree.topLevelItem(0).text(0) == "Presse 7"
    assert not page.tree.topLevelItem(0).icon(0).isNull()


def test_customer_with_assets_cannot_be_deleted(window, monkeypatch):
    errors = []
    monkeypatch.setattr("easymeasurement.ui.master_data.show_error", lambda _, t: errors.append(t))
    monkeypatch.setattr(QMessageBox, "question", lambda *_: QMessageBox.StandardButton.Yes)
    page = window.master_data
    page.customers.setCurrentRow(0)
    page._delete()
    assert errors and page.customers.count() == 2


def test_deleting_master_data_asks_first(window):
    page = window.master_data
    customer = window.app.db.add_customer("Leer GmbH")
    page.refresh()
    page.select_customer(customer)
    page._delete()  # the default answer in tests is no
    assert window.app.db.customer(customer) is not None


def test_a_field_is_kept_when_moving_on(window):
    page = window.master_data
    page.customers.setCurrentRow(0)
    customer = page.customer_id()
    page.customer_form.fields["city"].setText("Bonn")
    page.customer_form.fields["city"].editingFinished.emit()
    page.customers.setCurrentRow(1)
    assert window.app.db.customer(customer)["city"] == "Bonn"


def test_an_element_shows_the_features_of_its_kind(window):
    page = window.master_data
    page.customers.setCurrentRow(0)
    page.tree.setCurrentItem(page.tree.topLevelItem(0))  # a machine
    form = page.element_form
    assert page.forms.currentWidget() is form
    assert form.features.title() == "Merkmale: Maschine"
    form.feature_fields["rated_current"].setText("16")
    form.feature_fields["rated_current"].editingFinished.emit()
    asset = page.tree.current_id()
    assert window.app.db.asset_features(asset) == {"rated_current": "16"}


def test_closed_campaign_offers_no_new_measurement(window):
    window.app.service.close(window.first)
    page = window.measurements
    page.campaign.setCurrentIndex(page.campaign.findData(window.first))
    page.table.setCurrentCell(0, 0)
    assert not page.edit_measurement.isEnabled()
    window.campaign.show_campaign(window.first)
    assert not window.campaign.values.manual_action.isEnabled()
    assert not window.campaign.finish_action.isEnabled()


def test_report_list_finds_a_generated_report(window):
    app = window.app
    app.service.close(window.first)
    app.archive.generate(window.first, "Standardprotokoll", app.db.templates()[0]["body"])
    page = window.reports
    page.refresh()
    assert page.table.rowCount() == 1
    assert page.table.item(0, 8).text() == "unverändert"
    page.text.setText("nordwerk")
    assert page.table.rowCount() == 0


def test_terminating_the_program_exits_in_an_orderly_way(tmp_path):
    """Only an orderly exit lets a driver leave Push/Print on the instrument."""
    environment = {
        **os.environ, "QT_QPA_PLATFORM": "offscreen", "EASYMEASUREMENT_DATA": str(tmp_path),
    }
    process = subprocess.Popen([sys.executable, "-m", "easymeasurement"], env=environment)
    time.sleep(3)
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=10) == 0
