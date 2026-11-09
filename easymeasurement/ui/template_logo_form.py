# EasyMeasurement - easymeasurement/ui/template_logo_form.py
# The logo block of the template editor: embedding an image and placing it on the page.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QSize, Qt
from PySide6.QtGui import QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)

from ..reporting.logo import (
    MIN_WIDTH_MM,
    PAGE_HEIGHT_MM,
    PAGE_WIDTH_MM,
    PRESETS,
    LogoError,
    clamp_placement,
    decode_logo,
    logo_ratio,
    prepare_logo,
)
from .common import show_error
from .logo_placer import LogoPlacer

_SVG_PIXELS = 1000


def read_image_file(path: Path) -> bytes:
    """Return raster image bytes. Vector logos are drawn to a transparent bitmap first."""
    if path.suffix.lower() != ".svg":
        return path.read_bytes()
    renderer = QSvgRenderer(str(path))
    if not renderer.isValid():
        raise LogoError("Die SVG-Datei ist nicht lesbar.")
    size = renderer.defaultSize()
    size.scale(QSize(_SVG_PIXELS, _SVG_PIXELS), Qt.AspectRatioMode.KeepAspectRatio)
    image = QImage(size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(buffer.data())


class TemplateLogoForm:
    """Position, width and pages of the logo, on a small page and in figures."""

    def import_logo(self, path: Path) -> bool:
        """Embed an image into the selected logo block."""
        block = self._block(self.path())
        try:
            key, encoded = prepare_logo(read_image_file(path))
        except (LogoError, OSError) as err:
            show_error(self, str(err))
            return False
        self.template.setdefault("images", {})[key] = encoded
        block["image"] = key
        ratio = logo_ratio(decode_logo(encoded))
        block["x_mm"], block["y_mm"], block["width_mm"] = clamp_placement(
            block["x_mm"], block["y_mm"], block["width_mm"], ratio
        )
        self._show_form()
        self._changed()
        return True

    def _choose_logo(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Logo wählen", "", "Bilder (*.png *.jpg *.jpeg *.webp *.bmp *.svg)"
        )
        if name:
            self.import_logo(Path(name))

    def _form_logo(self, block: dict, form: QFormLayout) -> None:
        choose = QPushButton("Bild ersetzen …" if block.get("image") else "Bild wählen …")
        choose.clicked.connect(self._choose_logo)
        form.addRow(choose)
        if not block.get("image"):
            form.addRow(QLabel("PNG, JPEG, WebP oder SVG. Transparenz bleibt erhalten."))
            return
        data = decode_logo(self.template["images"][block["image"]])
        ratio = logo_ratio(data)
        pixmap = QPixmap()
        pixmap.loadFromData(data)

        placer = LogoPlacer()
        placer.set_logo(pixmap, ratio)
        placer.set_placement(block["x_mm"], block["y_mm"], block["width_mm"])
        x = QDoubleSpinBox(suffix=" mm", decimals=1, maximum=PAGE_WIDTH_MM)
        y = QDoubleSpinBox(suffix=" mm", decimals=1, maximum=PAGE_HEIGHT_MM)
        width = QDoubleSpinBox(suffix=" mm", decimals=1, minimum=MIN_WIDTH_MM, maximum=PAGE_WIDTH_MM)
        height = QLabel()
        preset = QComboBox()
        preset.addItem("Schnellposition …", None)
        for index, (label, _) in enumerate(PRESETS):
            preset.addItem(label, index)

        def show(px: float, py: float, pw: float) -> None:
            for box, value in ((x, px), (y, py), (width, pw)):
                box.blockSignals(True)
                box.setValue(value)
                box.blockSignals(False)
            shown = f"{pw * ratio:.1f}".replace(".", ",")
            height.setText(f"{shown} mm (Seitenverhältnis bleibt erhalten)")

        def apply(px: float, py: float, pw: float) -> None:
            px, py, pw = clamp_placement(px, py, pw, ratio)
            block["x_mm"], block["y_mm"], block["width_mm"] = round(px, 1), round(py, 1), round(pw, 1)
            placer.set_placement(px, py, pw)
            show(px, py, pw)
            self._changed()

        def from_boxes() -> None:
            apply(x.value(), y.value(), width.value())

        def preset_chosen(index: int) -> None:
            choice = preset.itemData(index)
            if choice is not None:
                pw = block["width_mm"]
                apply(*PRESETS[choice][1](pw, pw * ratio), pw)
                preset.setCurrentIndex(0)

        placer.placementChanged.connect(apply)
        x.valueChanged.connect(from_boxes)
        y.valueChanged.connect(from_boxes)
        width.valueChanged.connect(from_boxes)
        preset.activated.connect(preset_chosen)
        show(block["x_mm"], block["y_mm"], block["width_mm"])

        pages = QComboBox()
        pages.addItem("Nur erste Seite", "first")
        pages.addItem("Jede Seite", "all")
        pages.setCurrentIndex(max(pages.findData(block.get("pages", "first")), 0))
        pages.currentIndexChanged.connect(
            lambda: (block.__setitem__("pages", pages.currentData()), self._changed())
        )
        reserve = QCheckBox("Text weicht dem Logo aus")
        reserve.setChecked(block.get("reserve", True))
        reserve.toggled.connect(lambda v: (block.__setitem__("reserve", v), self._changed()))

        self.logo_placer, self.logo_preset = placer, preset
        self.logo_x, self.logo_y, self.logo_width = x, y, width
        self.logo_pages, self.logo_reserve = pages, reserve
        side = QFormLayout()
        side.addRow("Position", preset)
        side.addRow("Von links", x)
        side.addRow("Von oben", y)
        side.addRow("Breite", width)
        side.addRow("Höhe", height)
        side.addRow("Seiten", pages)
        side.addRow(reserve)
        line = QHBoxLayout()
        line.addWidget(placer, 0, Qt.AlignmentFlag.AlignTop)
        line.addLayout(side, 1)
        form.addRow(line)
