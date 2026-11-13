# OkeyDocu - tests/crash_child.py
# Measures part of a guided round with the simulator, then ends its process at once.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Run as `python -m tests.crash_child` in a process of its own, with OKEYDOCU_DATA
set. The first step is measured and finished, the second is set up and holds two readings when
the process ends without closing anything, as a crash or an empty battery would end it. The
last line on stdout names the campaign and how many readings it holds by then."""
import os

from PySide6.QtWidgets import QApplication

CRASHED = 70  # the exit code the test expects; any other means the round failed before


def main() -> None:
    qt = QApplication([])
    from okeydocu.__main__ import build_context
    from okeydocu.campaign.plan import load_plans
    from okeydocu.ui import common
    from okeydocu.ui.main_window import MainWindow

    from .guided_helpers import connect_all, run_step

    common.SIMULATED_FAILURE_RATE = 0.0
    app = build_context()
    customer = app.db.add_customer("Musterbau GmbH")
    asset = app.db.add_asset(customer, "machine", "Presse 7")
    window = MainWindow(app)
    window.resize(1360, 900)
    window.show()
    page = window.guided
    campaign = page.start_campaign(asset, load_plans()[0], "Prüfung", "Prüfer", "simulator")
    run_step(page, readings=3)
    connect_all(page)
    page.confirm_button.click()
    page.simulate_button.click()
    page.simulate_button.click()
    qt.processEvents()
    count = len(app.service.measurements(campaign))
    print(f"campaign {campaign} readings {count}", flush=True)
    os._exit(CRASHED)


if __name__ == "__main__":
    main()
