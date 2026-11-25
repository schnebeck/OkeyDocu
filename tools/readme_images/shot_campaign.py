# OkeyDocu - tools/readme_images/shot_campaign.py
# Pictures of the overview and of the campaign workspace.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Writes overview and campaign, and the upper part of the workspace for the picture of both
languages."""
from PySide6.QtCore import QRect

import demo
from staging import LANG, breeze, connected_prime, go_live, save

OPEN_POINT = 5  # the row of the first point still to be measured


def test_campaign(window, app, qtbot, monkeypatch):
    breeze()
    connected_prime(monkeypatch)
    ids = demo.plant(app, LANG)
    first, second, pattern = demo.history(app, ids, LANG)
    template = app.db.default_template()
    app.archive.generate(second, template["name"], template["body"], LANG)
    campaign = demo.running(app, ids, LANG, pattern)
    demo.inspect(app, campaign, window.guided.plans)
    window.resize(1440, 780)
    window.campaign.refresh()
    qtbot.wait(300)
    save(window, f"overview-{LANG}")
    page = window.campaign
    go_live(page, campaign, qtbot)
    window.resize(1560, 900)
    qtbot.wait(300)
    page.values.table.selectRow(OPEN_POINT)
    qtbot.wait(500)
    save(window, f"campaign-{LANG}")
    top = page.header.mapTo(window, page.header.rect().topLeft()).y()
    save(window, f"languages-{LANG}", QRect(0, top - 8, 1560, 560 - top))
