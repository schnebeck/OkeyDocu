# OkeyDocu - tests/test_logo_editor.py
# Placing a logo in the template editor, up to the archived report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import subprocess
from datetime import datetime

import pytest
from PIL import Image
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest

from okeydocu.__main__ import build_context
from okeydocu.model import Quantity, ResultValue
from okeydocu.reporting.logo import decode_logo
from okeydocu.reporting.template import parse_template
from okeydocu.ui import template_logo_form
from okeydocu.ui.main_window import MainWindow

from .logo_helpers import png


@pytest.fixture
def page(qtbot):
    app = build_context()
    main = MainWindow(app)
    main.resize(1360, 860)
    qtbot.addWidget(main)
    main.show()
    main.open_page(main.templates)
    yield main.templates
    app.db.close()


@pytest.fixture
def placed(page, tmp_path):
    source = tmp_path / "firma.png"
    source.write_bytes(png(400, 200))
    page._select((0,))
    page.add_block("logo")
    assert page.import_logo(source)
    return page


def block(page):
    return page._block(page.path())


def test_new_logo_block_asks_for_an_image(page):
    page._select((0,))
    page.add_block("logo")
    assert "noch kein Bild" in page.tree.currentItem().text(0)
    assert page.preview()


def test_import_embeds_the_image_in_the_template(placed):
    text = placed.current_text()
    assert "images:" in text
    assert block(placed)["image"] in parse_template(text)["images"]
    assert "erste Seite" in placed.tree.currentItem().text(0)


def test_import_of_a_broken_file_changes_nothing(page, tmp_path, monkeypatch):
    errors = []
    monkeypatch.setattr(template_logo_form, "show_error", lambda _, text: errors.append(text))
    bad = tmp_path / "kaputt.png"
    bad.write_bytes(b"nichts")
    page._select((0,))
    page.add_block("logo")
    assert not page.import_logo(bad)
    assert errors and not block(page)["image"]


def test_svg_logo_is_imported_with_transparency(page, tmp_path):
    source = tmp_path / "firma.svg"
    source.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100">'
        '<rect width="100" height="100" fill="#dc1414"/></svg>'
    )
    page._select((0,))
    page.add_block("logo")
    assert page.import_logo(source)
    data = decode_logo(page.template["images"][block(page)["image"]])
    with Image.open(io.BytesIO(data)) as image:
        assert image.size == (1000, 500)
        assert image.convert("RGBA").getpixel((900, 250))[3] == 0


def test_spin_boxes_place_and_scale(placed):
    placed.logo_x.setValue(30)
    placed.logo_y.setValue(40)
    placed.logo_width.setValue(80)
    assert (block(placed)["x_mm"], block(placed)["y_mm"], block(placed)["width_mm"]) == (30, 40, 80)
    assert placed.logo_placer.x_mm == 30


def test_spin_box_cannot_push_the_logo_off_the_page(placed):
    placed.logo_x.setValue(30)
    placed.logo_width.setValue(200)
    assert block(placed)["x_mm"] + block(placed)["width_mm"] <= 210


def test_drag_moves_the_logo(placed):
    view = placed.logo_placer
    placed.logo_x.setValue(50)
    placed.logo_y.setValue(50)
    start = view.logo_rect().center().toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view, start + QPoint(40, 30))
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=start + QPoint(40, 30))
    assert block(placed)["x_mm"] == pytest.approx(50 + 40 / view.scale, abs=1)
    assert block(placed)["y_mm"] == pytest.approx(50 + 30 / view.scale, abs=1)
    assert placed.logo_x.value() == block(placed)["x_mm"]


def test_drag_on_the_corner_scales_the_logo(placed):
    view = placed.logo_placer
    placed.logo_x.setValue(20)
    placed.logo_y.setValue(20)
    before = block(placed)["width_mm"]
    corner = view.logo_rect().bottomRight().toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=corner)
    QTest.mouseMove(view, corner + QPoint(40, 0))
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=corner + QPoint(40, 0))
    assert block(placed)["width_mm"] == pytest.approx(before + 40 / view.scale, abs=1)
    assert (block(placed)["x_mm"], block(placed)["y_mm"]) == (20, 20)


def test_drag_stops_at_the_page_edge(placed):
    view = placed.logo_placer
    start = view.logo_rect().center().toPoint()
    QTest.mousePress(view, Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view, QPoint(view.width() - 1, 1))
    QTest.mouseRelease(view, Qt.MouseButton.LeftButton, pos=QPoint(view.width() - 1, 1))
    assert block(placed)["y_mm"] == 0
    assert block(placed)["x_mm"] + block(placed)["width_mm"] == pytest.approx(210, abs=0.2)


@pytest.mark.parametrize("index,x,y", [(0, 18, 8), (2, 152, 8), (3, 18, 261), (5, 152, 261)])
def test_quick_positions(placed, index, x, y):
    placed.logo_width.setValue(40)  # 40 x 20 mm
    placed.logo_preset.setCurrentIndex(index + 1)
    placed.logo_preset.activated.emit(index + 1)
    assert (block(placed)["x_mm"], block(placed)["y_mm"]) == (x, y)


def test_pages_and_reserve_are_stored(placed):
    placed.logo_pages.setCurrentIndex(1)
    placed.logo_reserve.setChecked(False)
    assert block(placed)["pages"] == "all" and block(placed)["reserve"] is False


def test_logo_never_goes_into_a_repeat(placed):
    assert not placed.into_button.isEnabled()
    placed.add_block("steps")
    repeat = placed.path()[0]
    placed.add_block("text")
    placed._select((repeat, 0))
    placed.add_block("logo")
    assert len(placed.path()) == 1


def test_logo_survives_saving_and_reloading(placed):
    block(placed)["x_mm"] = 12.5
    placed._save()
    key = block(placed)["image"]
    placed.reload()
    stored = next(b for b in placed.template["blocks"] if b["type"] == "logo")
    assert stored["x_mm"] == 12.5 and stored["image"] == key
    placed._select((placed.template["blocks"].index(stored),))
    assert placed.logo_x.value() == 12.5


def test_logo_reaches_the_archived_report(placed, tmp_path):
    placed._save()
    app = placed.app
    customer = app.db.add_customer("Musterbau GmbH")
    asset = app.db.add_asset(customer, "machine", "Presse 7")
    campaign = app.service.create(asset, "Prüfung", "Prüfer")
    value = ResultValue("u", "U", Quantity.parse("230V"))
    app.service.add_measurement(campaign, "u", [value], datetime(2026, 3, 1))
    app.service.close(campaign)
    template = app.db.templates()[0]
    report_id = app.archive.generate(campaign, template["name"], template["body"])
    report = app.db.one("SELECT * FROM reports WHERE id=?", report_id)
    path = app.archive.path(report)
    listing = subprocess.run(["pdfimages", "-list", str(path)], capture_output=True, text=True).stdout
    assert "400" in listing and "200" in listing
    assert "images:" in report["template_body"]
