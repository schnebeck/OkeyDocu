# OkeyDocu - tools/readme_images/shot_photos.py
# Pictures of the photo view with marks and of the photo timeline.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes photo-marks and the frames of the timeline while the photos move onto their time.
Needs the sources shot_guide.py writes."""
import math

from PySide6.QtCore import QRect

from okeydocu.campaign.photo_marks import PhotoMark
from okeydocu.ui.photo_preview import PhotoPreview
from okeydocu.ui.photo_shared import shared_thumbs

import demo
import pictures
from staging import LANG, OUT, breeze, save

SOURCES = {"dial": f"{OUT}sharp-dial-{LANG}.png", "leads": f"{OUT}sharp-leads-{LANG}.png"}
TEXTS = ("Test button sticks", "Label of the circuit missing")  # what the marks say
AHEAD_S = 150  # what the camera's clock runs ahead
FRAMES = 22


def marked(app, campaign, window, qtbot) -> None:
    """The last photo with two marks, classed as a defect, in the photo view."""
    last = app.service.photos(campaign)[-1]
    marks = [PhotoMark(1, 0.735, 0.375, 0.072, 0.105, TEXTS[0]),
             PhotoMark(2, 0.47, 0.505, 0.215, 0.15, TEXTS[1])]
    app.service.save_photo_notes(last["id"], "defect", marks)
    path = app.service.photo_path(campaign, last["file_name"])
    preview = PhotoPreview(demo.WORDS[LANG]["rcd"], "RCD I\u0394N", path, window, app, last["id"])
    preview._open()
    qtbot.wait(600)
    save(preview.card, f"photo-marks-{LANG}")
    preview._close()
    app.service.save_photo_notes(last["id"], "", [])


def test_photos(window, app, qtbot, tmp_path):
    breeze()
    ids = demo.plant(app, LANG)
    campaign = demo.open_campaign(app, ids, demo.WORDS[LANG]["now"], LANG)
    demo.measure_round(app, campaign, ids, demo.DAY, 6)
    app.service.import_photos(campaign, pictures.series(SOURCES, tmp_path, demo.DAY, AHEAD_S))
    page = window.campaign
    window.resize(1360, 842)
    page.refresh()
    page.show_campaign(campaign)
    qtbot.wait(300)
    marked(app, campaign, window, qtbot)

    window.resize(1290, 745)
    page.timeline_action.setChecked(True)
    page.work.setSizes([sum(page.work.sizes()) - 215, 215])
    qtbot.wait(400)
    shared_thumbs().finish()
    qtbot.wait(400)
    corner = page.board.mapTo(window, page.board.rect().topLeft())
    bottom = page.timeline.mapTo(window, page.timeline.rect().bottomLeft()).y() + 1
    area = QRect(corner.x(), corner.y(), page.board.width(), bottom - corner.y())
    for frame in range(FRAMES + 1):
        eased = 0.5 - 0.5 * math.cos(math.pi * frame / FRAMES)  # starts and ends gently
        page.timeline._shift(-AHEAD_S * eased)
        qtbot.wait(120)
        save(window, f"timeline-{LANG}-{frame:02d}", area)
