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
from .l10n import tr
from .campaign.service import CampaignService
from .paths import data_dir
from .reporting.archive import ReportArchive
from .reporting.template import SHIPPED, shipped_template_text
from .reporting.template_model import in_program_language
from .store import Database, SchemaMismatch


def build_context():
    from .ui.common import AppContext

    root = data_dir()
    db = Database(root / "easymeasurement.sqlite")
    if not db.templates():
        for file, name in SHIPPED.items():
            db.save_template(tr(name), in_program_language(shipped_template_text(file)))
    service = CampaignService(db, root, KWalletKeyStore())
    service.seed_plans()
    return AppContext(db, service, ReportArchive(service))


def choose_language(application) -> None:
    """The language stored in the settings, or the system's. Qt's own words, such as the
    context menu of a text field, follow it, and so do numbers in spin boxes."""
    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator

    from .l10n import current, set_language
    from .ui.language_choice import chosen_language

    set_language(chosen_language())
    QLocale.setDefault(QLocale(current()))
    translator = QTranslator(application)
    folder = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load(f"qtbase_{current()}", folder):
        application.installTranslator(translator)


def program_icon():
    """The program's own picture, for the window manager and the task bar."""
    from importlib import resources

    from PySide6.QtGui import QIcon

    return QIcon(str(resources.files("easymeasurement") / "data" / "icons" / "easymeasurement.svg"))


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from .ui.main_window import MainWindow

    application = QApplication(sys.argv)
    application.setApplicationName("EasyMeasurement")
    application.setDesktopFileName("easymeasurement")
    application.setWindowIcon(program_icon())
    choose_language(application)
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
