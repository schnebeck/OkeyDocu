# OkeyDocu - okeydocu/ui/campaign_plans.py
# The test plans of the campaign on screen: listed at the side, run in place of the table.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""The campaign shows its structure and measurements; a plan takes the middle only while it
is run. Each campaign remembers the plan it runs, so switching campaigns and back finds it
where it was."""
from __future__ import annotations

from ..campaign.plan_blocks import PlanBlock
from ..campaign.point_plans import has_points
from ..l10n import tr
from .guided_pages import ReasonOverlay
from .plan_list import PlanList, ask_remove
from .plan_run import PlanRun


class CampaignPlans:
    def _build_plans(self) -> None:
        self.plan_runs: dict[int, tuple[int, ...]] = {}  # campaign → step ids of the plan run
        self.plan_list = PlanList()
        self.plan_list.run_requested.connect(self.run_plan)
        self.plan_list.remove_requested.connect(self.remove_plan)
        self.plan_list.assign_requested.connect(self.assign_plan)
        self.plan_run = PlanRun(self.guided)
        self.plan_run.paused.connect(self.pause_plan)
        self.plan_run.end_requested.connect(self.end_plan)
        self.plan_run.by_hand_requested.connect(lambda: self.values.manual_action.trigger())

    def _has_plans(self, campaign) -> bool:
        """A repeat inspection is filled in any order; it is no plan to be led through."""
        return bool(campaign["plan_key"]) and not has_points(campaign["plan_key"])

    def running_block(self) -> PlanBlock | None:
        run = self.plan_runs.get(self.campaign_id) if self.campaign_id else None
        if run is None:
            return None
        return next((block for block in self.app.service.plan_blocks(self.campaign_id)
                     if block.step_ids == run), None)

    def _show_plans(self, campaign) -> None:
        running = self.running_block() if campaign["status"] == "open" else None
        if running is None:
            self.plan_runs.pop(campaign["id"], None)
        blocks = self.app.service.plan_blocks(campaign["id"]) if self._has_plans(campaign) else []
        self.plan_list.show_blocks(blocks, campaign["status"] == "open", running)
        self.plan_section.setVisible(self._has_plans(campaign))
        if running is not None:
            self.plan_run.show_title(running.title)
        self.values.in_plan = running is not None
        self.plan_run.hand_button.setEnabled(running is not None)
        self.middle.setCurrentWidget(self.plan_run if running is not None else self.work)

    def run_plan(self, block: PlanBlock) -> None:
        if self.campaign_id is None:
            return
        self.plan_runs[self.campaign_id] = block.step_ids
        self.show_campaign(self.campaign_id)
        self.guided.select_step(self.app.service.first_open_step(block))

    def _started(self, campaign_id: int) -> None:
        """A campaign started with a plan goes straight into it."""
        blocks = self.app.service.plan_blocks(campaign_id)
        if blocks and self._has_plans(self.app.service.campaign(campaign_id)):
            self.plan_runs[campaign_id] = blocks[0].step_ids
        self.enter(campaign_id)
        if campaign_id in self.plan_runs:
            self.guided.select_step(self.app.service.first_open_step(blocks[0]))

    def pause_plan(self) -> None:
        if self.campaign_id is None:
            return
        self.app.service.pause_plans(self.campaign_id)
        self.plan_runs.pop(self.campaign_id, None)
        self._after_plan_change()

    def end_plan(self) -> None:
        block = self.running_block()
        if block is None:
            return
        overlay = ReasonOverlay(self, tr("End test plan"))
        overlay.ok_button.setText(tr("End plan"))
        if not overlay.exec():
            return
        self.app.service.end_plan(block, overlay.reason.toPlainText().strip())
        self.plan_runs.pop(self.campaign_id, None)
        self._after_plan_change()

    def remove_plan(self, block: PlanBlock) -> None:
        if self.campaign_id is None:
            return
        if not ask_remove(self, block, self.app.service.booked_on(block)):
            return
        if self.plan_runs.get(self.campaign_id) == block.step_ids:
            self.plan_runs.pop(self.campaign_id)
        self.app.service.remove_plan(self.campaign_id, block)
        self._after_plan_change()

    def _after_plan_change(self) -> None:
        self.show_campaign(self.campaign_id)
        self.list.update_campaign(self.campaign_id)
        self.changed.emit()
