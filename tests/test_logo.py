# EasyMeasurement - tests/test_logo.py
# Logo import, scaling and placement, checked in the rendered PDF.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import io
import re
import subprocess

import pytest
from PIL import Image

from easymeasurement.reporting.logo import LogoError, clamp_placement, decode_logo, prepare_logo
from easymeasurement.reporting.pdf import render_pdf
from easymeasurement.reporting.template import Heading, Logo, TemplateError, parse_template, resolve
from easymeasurement.reporting.template_model import dump_template, new_block

from .logo_helpers import RED, png

DPI = 72
PT_PER_MM = 72 / 25.4


def render(tmp_path, logos, heading=True, rows=0):
    nodes = list(logos)
    if heading:
        nodes.append(Heading("Prüfprotokoll"))
    from easymeasurement.reporting.template import Paragraph

    nodes += [Paragraph(f"Zeile {n}") for n in range(rows)]
    path = tmp_path / "logo.pdf"
    render_pdf(nodes, path)
    return path


def page_image(path, page=1):
    prefix = path.with_suffix("")
    subprocess.run(
        ["pdftoppm", "-r", str(DPI), "-f", str(page), "-l", str(page), "-png", str(path),
         str(prefix)],
        check=True,
    )
    return Image.open(sorted(path.parent.glob(f"{prefix.name}-*{page}.png"))[0]).convert("RGB")


def is_red(pixel):
    return pixel[0] > 180 and pixel[1] < 80


def at_mm(image, x, y):
    return image.getpixel((round(x * PT_PER_MM), round(y * PT_PER_MM)))


def logo(x=150, y=10, width=40, **options):
    return Logo(png(), x, y, width, **options)


def test_logo_lands_exactly_where_it_was_placed(tmp_path):
    image = page_image(render(tmp_path, [logo(100, 50, 60)]))
    assert is_red(at_mm(image, 130, 65))  # centre: 60 x 30 mm from (100, 50)
    assert is_red(at_mm(image, 102, 52)) and is_red(at_mm(image, 158, 78))
    assert not is_red(at_mm(image, 97, 65)) and not is_red(at_mm(image, 163, 65))
    assert not is_red(at_mm(image, 130, 47)) and not is_red(at_mm(image, 130, 83))


def test_width_scales_the_logo_and_keeps_proportions(tmp_path):
    image = page_image(render(tmp_path, [logo(20, 20, 100)]))
    assert is_red(at_mm(image, 118, 68))  # 100 x 50 mm
    assert not is_red(at_mm(image, 122, 45))
    assert not is_red(at_mm(image, 70, 73))


def page_count(path):
    text = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", text).group(1))


def test_first_page_only(tmp_path):
    path = render(tmp_path, [logo(150, 10, 40)], rows=120)
    assert page_count(path) >= 2
    assert is_red(at_mm(page_image(path, 1), 170, 20))
    assert not is_red(at_mm(page_image(path, 2), 170, 20))


def test_every_page(tmp_path):
    path = render(tmp_path, [logo(150, 10, 40, every_page=True)], rows=120)
    assert is_red(at_mm(page_image(path, 2), 170, 20))


def heading_top_mm(path):
    html = subprocess.run(
        ["pdftotext", "-bbox", "-f", "1", "-l", "1", str(path), "-"],
        capture_output=True, text=True,
    ).stdout
    match = re.search(r'yMin="([\d.]+)"[^>]*>Prüfprotokoll', html)
    return float(match.group(1)) / PT_PER_MM


def test_text_moves_below_a_tall_logo(tmp_path):
    path = render(tmp_path, [logo(20, 10, 100)])  # ends at 60 mm
    assert heading_top_mm(path) >= 60


def test_text_can_stay_under_the_logo(tmp_path):
    path = render(tmp_path, [logo(20, 10, 100, reserve=False)])
    assert heading_top_mm(path) < 30


def test_small_logo_above_the_margin_moves_nothing(tmp_path):
    path = render(tmp_path, [logo(150, 2, 10)])  # ends at 7 mm
    assert heading_top_mm(path) < 22


def test_logo_in_the_middle_of_the_page_does_not_push_text(tmp_path):
    path = render(tmp_path, [logo(50, 130, 100)])
    assert heading_top_mm(path) < 22


def test_transparency_survives(tmp_path):
    source = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    source.paste(RED + (255,), (0, 0, 100, 100))
    buffer = io.BytesIO()
    source.save(buffer, "PNG")
    _, encoded = prepare_logo(buffer.getvalue())
    image = page_image(render(tmp_path, [Logo(decode_logo(encoded), 50, 50, 100)]))
    assert is_red(at_mm(image, 75, 75))
    assert at_mm(image, 125, 75) == (255, 255, 255)  # see-through, not black


def test_large_image_is_reduced():
    key, encoded = prepare_logo(png(4000, 2000))
    with Image.open(io.BytesIO(decode_logo(encoded))) as image:
        assert image.size == (1000, 500)
    assert len(key) == 12


def test_same_image_gets_the_same_key():
    assert prepare_logo(png())[0] == prepare_logo(png())[0]


def test_sideways_phone_photo_is_turned_upright():
    source = Image.new("RGB", (400, 200), RED)
    exif = Image.Exif()
    exif[0x0112] = 6
    buffer = io.BytesIO()
    source.save(buffer, "JPEG", exif=exif)
    _, encoded = prepare_logo(buffer.getvalue())
    with Image.open(io.BytesIO(decode_logo(encoded))) as image:
        assert image.size == (200, 400)


def test_garbage_is_rejected():
    with pytest.raises(LogoError, match="kein lesbares Bild"):
        prepare_logo(b"das ist kein Bild")


def test_placement_stays_on_the_page():
    assert clamp_placement(500, 500, 40, 0.5) == (170, 277, 40)
    assert clamp_placement(-5, -5, 40, 0.5) == (0, 0, 40)
    assert clamp_placement(0, 0, 1, 1.0)[2] == 5
    assert clamp_placement(0, 0, 900, 0.5)[2] == 210
    x, y, width = clamp_placement(0, 0, 900, 3.0)  # tall logo: page height decides
    assert width == pytest.approx(99)


def test_images_come_last_and_unused_ones_disappear():
    key, encoded = prepare_logo(png())
    template = {
        "name": "Test",
        "images": {key: encoded, "alt": "AAAA"},
        "blocks": [{**new_block("logo"), "image": key}],
    }
    text = dump_template(template)
    assert text.index("blocks:") < text.index("images:")
    assert "alt:" not in text
    assert parse_template(text)["images"].keys() == {key}


def test_missing_image_is_reported():
    with pytest.raises(TemplateError, match="fehlt"):
        parse_template("blocks:\n  - {type: logo, image: abc}\n")


def test_logo_inside_a_repeat_is_rejected():
    block = {"type": "steps", "blocks": [new_block("logo")]}
    with pytest.raises(TemplateError, match="Wiederholung"):
        parse_template(dump_template({"blocks": [block]}))


def test_damaged_image_data_is_a_template_error():
    template = {"images": {"a": "%%%"}, "blocks": [{"type": "logo", "image": "a"}]}
    with pytest.raises(TemplateError, match="beschädigt"):
        resolve(template, {"campaign": {}, "steps": []})


def test_logo_block_without_an_image_renders_nothing():
    assert resolve({"blocks": [new_block("logo")]}, {"campaign": {}, "steps": []}) == []


def test_conditional_logo():
    key, encoded = prepare_logo(png())
    block = {**new_block("logo"), "image": key, "when": "device.overdue"}
    template = {"images": {key: encoded}, "blocks": [block]}
    base = {"campaign": {}, "steps": [], "device": {"overdue": False}}
    assert resolve(template, base) == []
