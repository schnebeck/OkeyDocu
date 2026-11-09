# EasyMeasurement - easymeasurement/ui/main_window.py
# The application window: the workspace, the menus, and the status that is always in sight.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import shutil
import sqlite3
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QFileDialog, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from .. import __version__
from ..importing.izytron import ImportFailed, import_day
from .campaign_page import CampaignPage
from .common import AppContext, show_error
from .dashboard_tiles import ARCHIVE, INSTRUMENT, MASTER_DATA, PLANS, TEMPLATES, USERS
from .main_menus import MainMenus
from .master_data import MasterDataPage
from .measurement_overlays import ImportOverlay
from .kinds_page import KindsPage
from .measurement_search import MeasurementsPage
from .plan_editor import PlanEditorPage
from .reports import ReportsPage
from .settings_dialog import SettingsOverlay
from .templates import TemplatesPage
from .users import UsersOverlay
from .view_memory import ViewMemory


class MainWindow(MainMenus, QMainWindow):
    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.memory = ViewMemory()
        self.setWindowTitle("EasyMeasurement")
        self.resize(1360, 820)
        self.measurements = MeasurementsPage(app)
        self.campaign = CampaignPage(app)
        self.guided = self.campaign.guided
        self.master_data = MasterDataPage(app)
        self.reports = ReportsPage(app)
        self.templates = TemplatesPage(app)
        self.plan_editor = PlanEditorPage(app)
        self.kinds = KindsPage(app)
        self.setCentralWidget(self.campaign)
        # Windows of their own, so they can stand beside a running campaign. No parent:
        # the window manager would otherwise keep them on top of the main window.
        self.page_windows = {
            self.measurements: self._page_window(self.measurements, "Alle Messwerte", 1200, 720),
            self.master_data: self._page_window(self.master_data, "Stammdaten", 900, 620),
            self.reports: self._page_window(self.reports, "Protokollarchiv", 1100, 620),
            self.templates: self._page_window(self.templates, "Vorlagen", 1200, 760),
            self.plan_editor: self._page_window(self.plan_editor, "Messpläne", 1200, 720),
            self.kinds: self._page_window(self.kinds, "Strukturtypen", 900, 640),
        }
        self._build_menus()
        self._build_status_bar()
        self._restore_view()

        self.campaign.report_requested.connect(self._make_report)
        self.campaign.master_data_requested.connect(lambda: self.open_page(self.master_data))
        self.campaign.page_requested.connect(self._open_tile)
        self.master_data.changed.connect(self.measurements.reload_choices)
        self.master_data.changed.connect(self.campaign.refresh)
        self.measurements.changed.connect(self._refresh_open_pages)
        self.measurements.changed.connect(self.guided.reload)
        self.measurements.changed.connect(self.campaign.refresh)
        self.campaign.changed.connect(self._refresh_open_pages)
        self.reports.changed.connect(self.campaign.reports_changed)
        self.kinds.changed.connect(self.campaign.refresh)
        self.kinds.changed.connect(self.master_data.refresh)
        self.master_data.kinds_requested.connect(lambda: self.open_page(self.kinds))

    def _page_window(self, page: QWidget, title: str, width: int, height: int) -> QWidget:
        window = QWidget()
        window.setWindowTitle(f"{title} – EasyMeasurement")
        window.resize(width, height)
        layout = QVBoxLayout(window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(page)
        return window

    def open_page(self, page: QWidget) -> None:
        if page is self.measurements:
            page.reload_choices()
        if page in (self.measurements, self.reports, self.plan_editor, self.master_data,
                    self.kinds):
            page.refresh()
        window = self.page_windows[page]
        window.show()
        window.raise_()
        window.activateWindow()

    def _refresh_open_pages(self) -> None:
        """Hidden pages catch up when they are opened: this runs after every reading."""
        if self.measurements.isVisible():
            self.measurements.reload_choices()
            self.measurements.refresh()
        if self.reports.isVisible():
            self.reports.refresh()

    def _open_tile(self, key: str) -> None:
        if key == USERS:
            UsersOverlay(self.app, self).exec()
            self.campaign.refresh()
        elif key == INSTRUMENT:
            self._open_settings()
        else:
            pages = {MASTER_DATA: self.master_data, PLANS: self.plan_editor,
                     TEMPLATES: self.templates, ARCHIVE: self.reports}
            self.open_page(pages[key])

    def _open_settings(self) -> None:
        SettingsOverlay(self).exec()

    def _about(self) -> None:
        QMessageBox.about(
            self, "Über EasyMeasurement",
            f"<b>EasyMeasurement {__version__}</b><br>Geführte Messungen, Prüfprotokolle und"
            " Archiv.<br><br>© 2026 Thorsten Schnebeck<br>GPL-3.0-or-later",
        )

    # Actions -------------------------------------------------------------

    def _make_report(self, campaign_id: int) -> None:
        self.reports.generate_for(campaign_id)
        self.campaign.reports_changed()

    def _import_izytron(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Kopie der IZYTRON-Datenbank wählen", "", "SQLite-Datenbank (*.sqlite *.db);;Alle (*)"
        )
        if not path:
            return
        dialog = ImportOverlay(self)
        if not dialog.exec():
            return
        try:
            # Never from the original: even reading can touch a SQLite database's side files.
            with tempfile.TemporaryDirectory() as folder:
                copy = Path(shutil.copy(path, folder))
                result = import_day(self.app.service, copy, dialog.offset.value())
        except ImportFailed as err:
            show_error(self, str(err))
            return
        except (OSError, sqlite3.Error):
            show_error(self, "Diese Datei ist keine lesbare IZYTRON-Datenbank.")
            return
        self.master_data.refresh()
        self.campaign.refresh()
        self.campaign.show_campaign(result.campaign_id)
        self.campaign.notice.setText(f"{result.measurements} Messungen importiert.")

    # Window --------------------------------------------------------------

    def _restore_view(self) -> None:
        memory = self.memory
        memory.restore_window("main", self)
        # Pinned first: the stored widths of the list belong to the splitter it stands in.
        memory.keep_toggle("list_pinned", self.list_action, default=False)
        memory.keep_splitters(self.campaign)
        for page, window in self.page_windows.items():
            memory.restore_window(type(page).__name__, window)
            memory.keep_splitters(page)
        for section in self.campaign.side.sections:
            memory.keep_section(section)
        memory.keep_toggle("side", self.side_action)
        memory.keep_toggle("timeline", self.campaign.timeline_action)

    def changeEvent(self, event) -> None:
        """Plans, templates and master data change in windows of their own."""
        if event.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self.campaign._refresh_home()
        super().changeEvent(event)

    def closeEvent(self, event) -> None:
        for view in (self.campaign.values, self.measurements):
            view.editor.apply()
        self.memory.store_window("main", self)
        self.campaign.shut_down()
        for page, window in self.page_windows.items():
            self.memory.store_window(type(page).__name__, window)
            window.close()
        super().closeEvent(event)
