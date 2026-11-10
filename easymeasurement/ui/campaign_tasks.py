# EasyMeasurement - easymeasurement/ui/campaign_tasks.py
# The actions of the campaign workspace, and the work on an open campaign behind them.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from PySide6.QtGui import QAction

from ..campaign.clock import CLOCK_SET_ACCURACY_S
from ..l10n import tr
from .campaign_edit import PLAN, TESTER, CampaignEditOverlay
from .campaign_views import AssignPlanOverlay, TesterOverlay


class CampaignTasks:
    """Menu, context menu and buttons share these actions; each works on the campaign shown."""

    def _build_actions(self) -> None:
        self.home_action = self._action(tr("Overview"), self.show_home)
        self.new_action = self._action(tr("New campaign …"), self.new_campaign)
        self.resume_action = self._action(tr("Resume measuring"), self.resume)
        self.pause_action = self._action(tr("Pause measuring"), self.pause)
        self.edit_action = self._action(tr("Edit campaign …"), self.edit_campaign)
        self.tester_action = self._action(tr("Change inspector …"), self.change_tester)
        self.assign_action = self._action(tr("Assign test plan …"), self.assign_plan)
        self.draft_action = self._action(tr("View report draft"), self.show_draft)
        self.finish_action = self._action(tr("Confirm report …"), self.finish)
        self.delete_action = self._action(tr("Delete campaign …"), self.delete_campaign)
        self.report_action = self._action(tr("Create report …"), self.make_report)
        self.photos_action = self._action(tr("Import photos …"), self.import_photos)
        # The timeline is a tool for placing photos: shown on asking, gone once they are placed.
        self.timeline_action = QAction(tr("Assign photos"), self, checkable=True, shortcut="F7")
        self.timeline_action.toggled.connect(self._fit_photo_panels)
        self.fetch_action = self._action(tr("Fetch from the instrument"), self.fetch)
        self.clock_action = self._action(tr("Set clock …"), self.check_clock)
        self.clock_action.setToolTip(tr("Checks the instrument clock and, after asking, sets it"
                                        " to the laptop time. Measurements with the old time"
                                        " come first."))
        self.offset_action = self._action(tr("Clock offset by hand …"), self.correct_clock)
        self.offset_action.setToolTip(tr("Only for measurements that lay in the instrument with"
                                         " a wrong clock, such as from an earlier day"))

    def _action(self, text: str, slot) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(lambda: slot())
        return action

    def assign_plan(self) -> None:
        overlay = AssignPlanOverlay(self.app.service.plans(), self)
        if overlay.exec():
            self.app.service.assign_plan(self.campaign_id, overlay.plan.currentData())
            self.show_campaign(self.campaign_id)
            self.list.update_campaign(self.campaign_id)
            self.changed.emit()

    def edit_campaign(self) -> None:
        campaign = self._campaign()
        if campaign is None or campaign["status"] != "open":
            return
        overlay = CampaignEditOverlay(self.app, campaign, self)
        if overlay.exec():
            asset = overlay.asset.currentData()
            self.app.service.update_campaign(campaign["id"], overlay.title.text(), asset)
            self.app.service.set_contact(campaign["id"], *overlay.contact_values())
            self.app.service.set_cost_center(campaign["id"], overlay.cost_center.text())
            self.list.update_campaign(campaign["id"])
            self.show_campaign(campaign["id"])
            self.changed.emit()
        follow = {TESTER: self.change_tester, PLAN: self.assign_plan}.get(overlay.follow_up)
        if follow is not None:
            follow()

    def change_tester(self) -> None:
        campaign = self._campaign()
        if campaign is None or campaign["status"] != "open":
            return
        count = self.app.service.measurement_counts().get(campaign["id"], 0)
        overlay = TesterOverlay(self.app, campaign, count, self)
        if overlay.exec():
            self.app.service.assign_tester(
                campaign["id"], overlay.tester.current_id(), overlay.measurements.isChecked()
            )
            self.show_campaign(campaign["id"])
            self.changed.emit()

    def fetch(self) -> None:
        result = self.instrument.fetch(self.campaign_id)
        if result is not None:
            self.notice.setText(tr("{count} new measurements from the instrument.",
                                   count=result["added"]))
            self.guided.reload()
            self._data_changed()

    def check_clock(self) -> None:
        offset = self.instrument.check_clock(self.campaign_id)
        if offset is not None:
            if abs(offset) < CLOCK_SET_ACCURACY_S:
                self.notice.setText(tr("Instrument clock is exact"))
            else:
                self.notice.setText(tr("Instrument clock is {offset} s off: please set it on"
                                       " the instrument", offset=f"{offset:+.0f}"))
        self.refresh()

    def correct_clock(self) -> None:
        if self.instrument.correct_clock(self.campaign_id):
            self.refresh()
