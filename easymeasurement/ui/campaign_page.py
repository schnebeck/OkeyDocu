# EasyMeasurement - easymeasurement/ui/campaign_page.py
# The workspace: every campaign on the left, the chosen one in the middle, its context on the right.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from .board import EDGE, GUTTER, Board, GutterSplitter
from .campaign_actions import CampaignActions
from .campaign_checks import CampaignChecks
from .campaign_confirm import CampaignConfirm
from .campaign_display import CampaignDisplay
from .campaign_header import CampaignHeader
from .campaign_list import CampaignList
from .campaign_photos import CampaignPhotos
from .campaign_places import CampaignPlaces
from .campaign_reports import CampaignReports
from .campaign_values import CampaignValues
from .campaign_views import FreeRunView
from .common import AppContext
from .dashboard import Dashboard
from .edge_drawer import EdgeDrawer
from .guided import GuidedPage
from .instrument_control import InstrumentControl
from .live_session import LiveSession
from .side_panel import SidePanel
from .structure_panel import PlacePanel, StructurePanel
from .status_badges import ClockBadge, LinkBadge


class CampaignPage(CampaignDisplay, CampaignActions, CampaignConfirm, CampaignPhotos,
                   CampaignPlaces, CampaignChecks, QWidget):
    """Choosing a campaign only shows it. The instrument stays with the one measuring."""

    changed = Signal()
    report_requested = Signal(int)
    master_data_requested = Signal()
    page_requested = Signal(str)

    def __init__(self, app: AppContext):
        super().__init__()
        self.app = app
        self.campaign_id: int | None = None  # the one on screen
        self.live_id: int | None = None  # the one the instrument measures for
        self.session: LiveSession | None = None
        self.instrument = InstrumentControl(app, self)

        self.list = CampaignList(app)
        self.home = Dashboard(app)
        self.header = CampaignHeader()
        self.guided = GuidedPage(app, self.instrument)
        self.free = FreeRunView(app)
        self.values = CampaignValues(app)

        # Status bar content: the main window shows it, whatever else is on screen.
        self.link = LinkBadge()
        self.link_state: tuple[str, str] | None = None
        self.clock = ClockBadge()
        self.summary = QLabel()
        self.notice = QLabel()
        self.notice.linkActivated.connect(lambda _: self.open_newest_report())

        self.structure_panel = StructurePanel(app)
        self.structure = self.structure_panel.tree
        self.structure.measurement_source = self.values.table
        self.place_targets: dict[int, int | None] = {}  # where new readings of a campaign go
        self.reports = CampaignReports(app)
        self.side = SidePanel()
        self.place = PlacePanel(app)
        self.place_files = self.place.files
        self.asset_section = self.side.add("Ort", self.place, grows=False)
        self.plan_add_button = QPushButton("Messplan zuweisen …")
        self.plan_add_button.clicked.connect(self.assign_plan)
        plan_box = QWidget()
        plan_layout = QVBoxLayout(plan_box)
        plan_layout.setContentsMargins(0, 0, 0, 0)
        plan_layout.addWidget(self.guided.steps, 1)
        plan_layout.addWidget(self.plan_add_button)
        self.plan_section = self.side.add("Messplan", plan_box)
        self.loose_section = self.side.add("Nicht zugeordnet", self.guided.open_box)
        self.detail_section = self.side.add("Messung", self.values.detail, grows=False)
        self.photo_section = self.side.add("Fotos", self.values.gallery)
        self._build_photos()
        self.stack_section = self.side.add("Nicht zugeordnete Fotos", self.stack)
        self.report_section = self.side.add("Protokolle", self.reports)
        # Until a campaign needs them. Shown, they would count towards the minimum window size.
        for section in (self.plan_section, self.loose_section, self.report_section,
                        self.stack_section):
            section.hide()

        self.work = GutterSplitter(Qt.Orientation.Vertical, objectName="campaign-panes",
                                   width=GUTTER // 2)
        self.work.addWidget(self.guided)
        # The structure and what was measured on it, side by side like folders and files.
        self.board = Board("campaign-board", self.structure_panel, self.values,
                           head=self.values.head)
        self.board.splitter.setStretchFactor(1, 1)
        self.board.splitter.setSizes([320, 900])
        self.work.addWidget(self.board)
        self.work.addWidget(self.timeline)
        # The table is what all of this is for, the step only tells how to get there.
        self.work.setStretchFactor(0, 1)
        self.work.setStretchFactor(1, 2)
        self.work.setStretchFactor(2, 0)
        self.work.setSizes([300, 460, 190])
        centre = QWidget()
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.addWidget(self.header)
        centre_layout.addWidget(self.free)
        centre_layout.addWidget(self.work, 1)
        self.running = GutterSplitter(objectName="campaign")
        self.running.addWidget(centre)
        self.running.addWidget(self.side)
        self.running.setStretchFactor(0, 1)
        self.running.setSizes([860, 280])
        self.pages = QStackedWidget()
        self.pages.addWidget(self.home)
        self.pages.addWidget(self.running)
        self.splitter = GutterSplitter(objectName="campaigns")
        self.splitter.addWidget(self.list)
        self.splitter.addWidget(self.pages)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([230, 1130])
        layout = QVBoxLayout(self)
        layout.setContentsMargins(EDGE, EDGE, EDGE, 0)
        layout.addWidget(self.splitter)
        # Not pinned, the list waits at the left edge and leaves the room to the work.
        self.drawer = EdgeDrawer(self)
        self.pin_list(False)

        self.home_action = self._action("Übersicht", self.show_home)
        self.new_action = self._action("Neue Kampagne …", self.new_campaign)
        self.resume_action = self._action("Messung fortsetzen", self.resume)
        self.pause_action = self._action("Messung unterbrechen", self.pause)
        self.edit_action = self._action("Kampagne bearbeiten …", self.edit_campaign)
        self.tester_action = self._action("Prüfer ändern …", self.change_tester)
        self.assign_action = self._action("Messplan zuweisen …", self.assign_plan)
        self.draft_action = self._action("Protokoll-Entwurf ansehen", self.show_draft)
        self.finish_action = self._action("Protokoll bestätigen …", self.finish)
        self.delete_action = self._action("Kampagne löschen …", self.delete_campaign)
        self.report_action = self._action("Protokoll erstellen …", self.make_report)
        self.photos_action = self._action("Fotos importieren …", self.import_photos)
        # The timeline is a tool for placing photos: shown on asking, gone once they are placed.
        self.timeline_action = QAction("Fotos zuordnen", self, checkable=True, shortcut="F7")
        self.timeline_action.toggled.connect(self._fit_photo_panels)
        self.fetch_action = self._action("Vom Gerät nachholen", self.fetch)
        self.clock_action = self._action("Uhr prüfen", self.check_clock)
        self.offset_action = self._action("Uhrenversatz von Hand …", self.correct_clock)

        self.list.new_button.clicked.connect(self.new_campaign)
        self.list.home_requested.connect(self.show_home)
        self.list.chosen.connect(self.show_campaign)
        self.list.resume_requested.connect(self._resume_from_list)
        self.home.start_requested.connect(self.new_campaign)
        self.home.master_data_requested.connect(self.master_data_requested)
        self.home.page_requested.connect(self.page_requested)
        self.home.campaign_requested.connect(self._from_home)
        self.home.due_requested.connect(self.new_campaign)
        self.header.tester_requested.connect(self.change_tester)
        self.header.edit_requested.connect(self.edit_campaign)
        self.header.home_requested.connect(self.show_home)
        self.header.check_requested.connect(self._follow_check)
        self.list.menu_requested.connect(self._campaign_menu)
        self.header.resume_button.clicked.connect(self.resume)
        self.header.pause_button.clicked.connect(self.pause)
        self.header.photos_button.clicked.connect(self.import_photos)
        self.header.assign_button.clicked.connect(
            lambda: self.timeline_action.setChecked(self.header.assign_button.isChecked()))
        self.header.finish_button.clicked.connect(self.finish)
        self.header.draft_button.clicked.connect(self.show_draft)
        self.header.report_button.clicked.connect(self.make_report)
        self.structure.chosen.connect(self._place_chosen)
        self.structure.changed.connect(self._data_changed)
        self.structure_panel.actions.properties_requested.connect(self._edit_element)
        self.place.properties_requested.connect(self._edit_element)
        self.place_files.changed.connect(self.changed)
        self._connect_photos()
        self.guided.started.connect(self.enter)
        self.guided.changed.connect(self._data_changed)
        self.guided.step_shown.connect(self.values.show_step)
        self.guided.loose_counted.connect(self._show_loose)
        self.values.changed.connect(self._data_changed)
        self.values.edit_requested.connect(self._show_editor)
        self.reports.changed.connect(self.changed)
        self._update()

    def pin_list(self, pinned: bool) -> None:
        """Pinned, the list stands beside the pages; otherwise it slides in at the edge."""
        if pinned:
            self.drawer.set_active(False)
            self.splitter.insertWidget(0, self.list)
        else:
            self.drawer.hold(self.list)
            self.drawer.set_active(True)
        self.list.show()

    def _action(self, text: str, slot) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(lambda: slot())
        return action

    def refresh(self) -> None:
        """Something outside changed, such as the master data or a measurement."""
        self._refresh_home()
        self.list.refresh()
        if self.campaign_id is not None:
            self.show_campaign(self.campaign_id)
        self._update()

    def _show_editor(self) -> None:
        self.detail_section.toggle.setChecked(True)

    def _data_changed(self) -> None:
        if self.campaign_id is not None:
            self.list.update_campaign(self.campaign_id)
            self.values.refresh()
            self._refresh_photos()
            self._refresh_structure()
        self._refresh_home()
        self._update()
        self.changed.emit()
