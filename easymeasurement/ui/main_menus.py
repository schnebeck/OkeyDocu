# EasyMeasurement - easymeasurement/ui/main_menus.py
# The menus of the main window and its status bar.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import QWidget

from .board import EDGE
from .users import UsersOverlay


class MainMenus:
    """Menus name the work, and the same actions stand behind the buttons."""

    def _build_menus(self) -> None:
        campaign, values = self.campaign, self.campaign.values
        bar = self.menuBar()

        menu = bar.addMenu("&Kampagne")
        campaign.new_action.setShortcut(QKeySequence.StandardKey.New)
        menu.addAction(campaign.new_action)
        self.import_action = menu.addAction("Aus IZYTRON importieren …")
        self.import_action.triggered.connect(self._import_izytron)
        menu.addSeparator()
        menu.addAction(campaign.resume_action)
        menu.addAction(campaign.pause_action)
        menu.addSeparator()
        menu.addAction(campaign.edit_action)
        menu.addAction(campaign.tester_action)
        menu.addAction(campaign.assign_action)
        menu.addAction(campaign.draft_action)
        menu.addAction(campaign.finish_action)
        campaign.report_action.setShortcut(QKeySequence.StandardKey.Print)
        menu.addAction(campaign.report_action)
        menu.addSeparator()
        menu.addAction(campaign.delete_action)
        menu.addSeparator()
        self.quit_action = menu.addAction("EasyMeasurement beenden")
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)

        menu = bar.addMenu("&Bearbeiten")
        menu.addAction(values.manual_action)
        menu.addAction(values.edit_action)
        menu.addAction(values.delete_action)
        menu.addSeparator()
        menu.addAction(values.photo_action)
        menu.addAction(campaign.photos_action)

        menu = bar.addMenu("&Ansicht")
        campaign.home_action.setShortcut(QKeySequence("Alt+Home"))
        menu.addAction(campaign.home_action)
        menu.addSeparator()
        self.drawer_action = menu.addAction("Kampagnenliste")
        self.drawer_action.setShortcut(QKeySequence("F9"))
        self.drawer_action.setToolTip("Klappt die Liste aus; die Maus am linken Fensterrand auch")
        self.drawer_action.triggered.connect(campaign.drawer.toggle)
        self.list_action = menu.addAction("Kampagnenliste anheften")
        self.list_action.setCheckable(True)
        self.list_action.toggled.connect(campaign.pin_list)
        self.list_action.toggled.connect(lambda pinned: self.drawer_action.setEnabled(not pinned))
        self.side_action = self._toggle(menu, "Seitenleiste", campaign.side)
        values.edit_requested.connect(lambda: self.side_action.setChecked(True))
        menu.addAction(campaign.timeline_action)
        menu.addSeparator()
        self.search_action = menu.addAction("Alle Messwerte durchsuchen …")
        self.search_action.setShortcut(QKeySequence.StandardKey.Find)
        self.search_action.triggered.connect(lambda: self.open_page(self.measurements))

        menu = bar.addMenu("&Messgerät")
        menu.addAction(campaign.fetch_action)
        menu.addSeparator()
        menu.addAction(campaign.clock_action)
        menu.addAction(campaign.offset_action)
        menu.addSeparator()
        self.instrument_action = menu.addAction("Messgerät einrichten …")
        self.instrument_action.triggered.connect(self._open_settings)

        menu = bar.addMenu("&Verwaltung")
        self.users_action = menu.addAction("Benutzer …")
        self.users_action.triggered.connect(lambda: UsersOverlay(self.app, self).exec())
        self.master_data_action = menu.addAction("Stammdaten …")
        self.master_data_action.triggered.connect(lambda: self.open_page(self.master_data))
        self.plans_action = menu.addAction("Messpläne …")
        self.plans_action.triggered.connect(lambda: self.open_page(self.plan_editor))
        self.templates_action = menu.addAction("Vorlagen …")
        self.templates_action.triggered.connect(lambda: self.open_page(self.templates))
        self.archive_action = menu.addAction("Protokollarchiv …")
        self.archive_action.triggered.connect(lambda: self.open_page(self.reports))

        menu = bar.addMenu("&Einstellungen")
        self.kinds_action = menu.addAction("Strukturtypen …")
        self.kinds_action.triggered.connect(lambda: self.open_page(self.kinds))
        self.settings_action = menu.addAction("EasyMeasurement einrichten …")
        self.settings_action.triggered.connect(self._open_settings)

        menu = bar.addMenu("&Hilfe")
        menu.addAction(campaign.free.instruction_action)
        menu.addSeparator()
        self.about_action = menu.addAction("Über EasyMeasurement")
        self.about_action.triggered.connect(self._about)

    def _toggle(self, menu, text: str, panel: QWidget) -> QAction:
        action = menu.addAction(text)
        action.setCheckable(True)
        action.setChecked(True)
        action.toggled.connect(panel.setVisible)
        return action

    def _build_status_bar(self) -> None:
        bar = self.statusBar()
        bar.setContentsMargins(EDGE, 0, EDGE, 0)
        for widget in (self.campaign.link, self.campaign.clock, self.campaign.summary):
            bar.addWidget(widget)
        bar.addPermanentWidget(self.campaign.notice)
