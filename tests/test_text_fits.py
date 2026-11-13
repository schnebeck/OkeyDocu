# OkeyDocu - tests/test_text_fits.py
# No text is cut off, in German or English, at the window widths a laptop or a desk shows.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import pytest
from PySide6.QtCore import QTimer

from okeydocu.l10n import set_language
from okeydocu.ui.main_window import MainWindow

from .text_fit import cut_texts
from .workspace_helpers import plan_title, start, with_asset

WIDTHS = range(900, 2101, 100)
SETTLE_MS = 30  # layouts follow a resize on the next turns of the event loop
PAGES = ("master_data", "reports", "templates", "plan_editor", "kinds", "measurements")


@pytest.fixture(params=["de", "en"])
def speaking_window(request, qtbot, app):
    set_language(request.param)
    main = MainWindow(app)
    qtbot.addWidget(main)
    main.show()
    yield main
    main.campaign.shut_down()
    set_language("de")


def _overlays(window, app):
    from okeydocu.ui.campaign_dialog import CampaignDialog
    from okeydocu.ui.company_form import CompanyForm
    from okeydocu.ui.instrument_log import InstrumentLogOverlay
    from okeydocu.ui.language_choice import LanguageOverlay
    from okeydocu.ui.settings_dialog import SettingsOverlay
    from okeydocu.ui.users import UsersOverlay
    return (("settings", lambda: SettingsOverlay(window, app)),
            ("instrument log", lambda: InstrumentLogOverlay(app, window)),
            ("company", lambda: CompanyForm(app, window)),
            ("users", lambda: UsersOverlay(app, window)),
            ("language", lambda: LanguageOverlay(window)),
            ("new campaign", lambda: CampaignDialog(app, window)))


def test_nothing_is_cut_off(speaking_window, app, qtbot, monkeypatch):
    window, found = speaking_window, []
    with_asset(window, app)
    for width in WIDTHS:
        window.resize(width, 900)
        qtbot.wait(SETTLE_MS)
        found += [f"start@{width}: {line}" for line in cut_texts(window)]
    for name in PAGES:
        page = getattr(window, name)
        window.open_page(page)
        frame = window.page_windows[page]
        for width in (1000, 1400, 1800):
            frame.resize(width, 800)
            qtbot.wait(SETTLE_MS)
            found += [f"{name}@{width}: {line}" for line in cut_texts(frame)]
        frame.hide()
    window.resize(1400, 900)
    for name, factory in _overlays(window, app):
        item = factory()
        QTimer.singleShot(100, lambda item=item, name=name: (
            found.extend(f"{name}: {line}" for line in cut_texts(item)), item.reject()))
        item.exec()
    start(window, monkeypatch, plan_title(window), simulated=True)
    for width in (1000, 1400, 1800):
        window.resize(width, 900)
        qtbot.wait(SETTLE_MS)
        found += [f"guided@{width}: {line}" for line in cut_texts(window)]
    assert not found, "\n".join(found)
