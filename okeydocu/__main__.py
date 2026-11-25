# OkeyDocu - okeydocu/__main__.py
# Application entry point.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import signal
import sys

from . import APP_NAME, TAGLINE
from .campaign.secret_key import SecretKeyStore
from .l10n import tr
from .campaign.service import CampaignService
from .paths import data_dir
from .reporting.archive import ReportArchive
from .reporting.template import SHIPPED, STANDARD, shipped_template_text
from .reporting.template_model import in_program_language
from .store import Database, SchemaMismatch


def build_context():
    from .ui.common import AppContext

    root = data_dir()
    db = Database(root / "okeydocu.sqlite")
    if not db.templates():
        for file, name in SHIPPED.items():
            db.save_template(tr(name), in_program_language(shipped_template_text(file)))
        db.set_default_template(tr(SHIPPED[STANDARD]))  # whatever the names sort like
    service = CampaignService(db, root, SecretKeyStore())
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

    return QIcon(str(resources.files("okeydocu") / "data" / "icons" / "okeydocu.svg"))


def options(arguments: list[str]):
    """What the command line asks for beyond the options Qt takes."""
    import argparse

    from .testprojects import PROJECTS

    parser = argparse.ArgumentParser(prog="okeydocu", description=TAGLINE)
    parser.add_argument("--testproject", choices=PROJECTS, metavar="NAME",
                        help="work on invented data of its own, ready to play with: "
                             + ", ".join(PROJECTS))
    parser.add_argument("--fresh", action="store_true",
                        help="with --testproject: begin the test project anew")
    return parser.parse_known_args(arguments)[0]


def main() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox

    from . import testprojects
    from .ui.main_window import MainWindow

    asked = options(sys.argv[1:])
    if asked.testproject:  # before anything opens the database
        testprojects.enter(asked.testproject, asked.fresh)
    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setDesktopFileName("okeydocu")
    application.setWindowIcon(program_icon())
    # An orderly exit lets instrument drivers leave Push/Print. A signal that comes while the
    # program is still starting quits it as soon as the event loop runs.
    for number in (signal.SIGINT, signal.SIGTERM):
        signal.signal(number, lambda *_: QTimer.singleShot(0, application.quit))
    choose_language(application)
    try:
        context = build_context()
    except SchemaMismatch as err:
        QMessageBox.critical(None, APP_NAME, str(err))
        return 1
    if asked.testproject:
        testprojects.prepare(context, asked.testproject)
    window = MainWindow(context)
    if asked.testproject:
        window.setWindowTitle(f"{APP_NAME} – {tr('Test project')} {asked.testproject}")
    window.show()
    # Python only sees a signal while it runs, hence the timer.
    heartbeat = QTimer(interval=250)
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start()
    return application.exec()


if __name__ == "__main__":
    sys.exit(main())
