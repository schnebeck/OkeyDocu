# OkeyDocu - tools/readme_images/shot_report.py
# Pictures of the settings warning and of a report.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes settings-check, a warning laid over the window it belongs to, and the pages of a
report."""
import subprocess
from datetime import timedelta

from PIL import Image, ImageDraw, ImageFilter

from okeydocu.devices import LiveReading
from okeydocu.model import MeterMeasurement, Parameter, Verdict

import demo
from staging import LANG, OUT, breeze, connected_prime, go_live, quiet, save

# What the instrument was set to, against 30 mA and type A on the rating plate.
WRONG = (Parameter("rated_residual_current", "300mA"), Parameter("rated_current", "40A"),
         Parameter("rcd_type", "AC"))
BOX_AT = (630, 395)  # where the middle of the warning's top edge lies in the window


def laid_over(window_path: str, box_path: str) -> Image.Image:
    """The warning is a window of its own; here it lies where the desktop would put it."""
    whole = Image.open(window_path).convert("RGB")
    card = Image.open(box_path).convert("RGB")
    left, top = BOX_AT[0] - card.width // 2, BOX_AT[1]
    shadow = Image.new("L", whole.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle(
        (left - 4, top + 2, left + card.width + 4, top + card.height + 12), 8, fill=120)
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    whole = Image.composite(Image.new("RGB", whole.size, (0, 0, 0)), whole, shadow)
    whole.paste(card, (left, top))
    ImageDraw.Draw(whole).rectangle(
        (left - 1, top - 1, left + card.width, top + card.height), outline=(150, 154, 158))
    return whole.crop((0, 0, 950, top + card.height + 40))


def test_settings(window, app, qtbot, monkeypatch):
    breeze()
    connected_prime(monkeypatch)
    ids = demo.plant(app, LANG)
    campaign = demo.open_campaign(app, ids, demo.WORDS[LANG]["now"], LANG)
    demo.take(app, campaign, ids["rcd"], "rcd_touch", demo.DAY + timedelta(minutes=9))
    page = window.campaign
    window.resize(1240, 760)
    page.refresh()
    go_live(page, campaign, qtbot)
    page.place_targets[campaign] = ids["rcd"]
    at = demo.DAY + timedelta(minutes=12)
    measurement = MeterMeasurement(
        uid="aaaaaaaa-0000-1000-8000-000000000002", function="rcd_time", taken_at=at,
        verdict=Verdict.PASSED, results=tuple(demo.readings("rcd_time")), parameters=WRONG)
    page._received(campaign, LiveReading(measurement, at))
    qtbot.wait(500)
    box = page.settings_warning
    assert box is not None and box.isVisible()
    page.values.table.setCurrentCell(-1, -1)
    page.values.table.clearSelection()
    quiet(page)
    qtbot.wait(200)
    whole = save(window, f"settings-window-{LANG}")
    laid_over(whole, save(box, f"settings-box-{LANG}")).save(f"{OUT}settings-check-{LANG}.png")
    box.accept()


def test_report(app):
    ids = demo.plant(app, LANG)
    campaign = demo.open_campaign(app, ids, demo.WORDS[LANG]["between"], LANG)
    demo.measure_round(app, campaign, ids, demo.DAY)
    app.service.close(campaign)
    template = app.db.default_template()
    report = app.archive.generate(campaign, template["name"], template["body"], LANG)
    row = next(found for found in app.archive.reports(campaign) if found["id"] == report)
    subprocess.run(["pdftoppm", "-png", "-r", "110", str(app.archive.path(row)),
                    f"{OUT}report-{LANG}"], check=True, timeout=60)
