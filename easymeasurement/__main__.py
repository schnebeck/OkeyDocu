# EasyMeasurement - easymeasurement/__main__.py
# Application entry point.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import signal
import sys

from .campaign.seal import KWalletKeyStore
from .campaign.service import CampaignService
from .paths import data_dir
from .reporting.archive import ReportArchive
from .reporting.template import default_template_text
from .store import Database, SchemaMismatch


def build_context():
    from .ui.common import AppContext

    root = data_dir()
    db = Database(root / "easymeasurement.sqlite")
    if not db.templates():
        db.save_template("Standardprotokoll", default_template_text())
    service = CampaignService(db, root, KWalletKeyStore())
    service.seed_plans()
    return AppContext(db, service, ReportArchive(service))


def speak_german(application) -> None:
    """The program speaks German, so Qt's own words do too: buttons, menus of text fields."""
    from PySide6.QtCore import QLibraryInfo, QTranslator

    translator = QTranslator(application)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_de", folder):
        application.installTranslator(translator)


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .ui.main_window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("EasyMeasurement")
    application.setDesktopFileName("easymeasurement")
    speak_german(application)
    try:
        context = build_context()
    except SchemaMismatch as err:
        QMessageBox.critical(None, "EasyMeasurement", str(err))
        return 1
    window = MainWindow(context)
    window.show()
    # An orderly exit lets instrument drivers leave Push/Print. Python only sees a
    # signal while it runs, hence the timer.
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: application.quit())
    heartbeat = QTimer(interval=250)
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
