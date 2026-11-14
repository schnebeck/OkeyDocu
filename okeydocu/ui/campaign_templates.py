# OkeyDocu - okeydocu/ui/campaign_templates.py
# Campaign templates in the campaign workspace: saving, taking one, following its points.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""After a reading took a point of a template, the readings go on to the element of the next
open point, so following the template's order needs no click on the laptop. Confirming a
campaign on an open template offers what it did differently to the template."""

from __future__ import annotations

from ..campaign.point_plans import is_template
from ..campaign.template_use import renamed
from ..campaign.templates import OPEN
from ..l10n import tr
from .template_overlays import TemplateCopyOverlay, TemplateLearnOverlay, TemplateSaveOverlay


class CampaignTemplates:
    """Mixed into the campaign page."""

    def save_as_template(self) -> None:
        campaign = self._campaign()
        if campaign is None:
            return
        overlay = TemplateSaveOverlay(campaign["title"], self)
        if overlay.exec():
            self.app.service.template_from(campaign["id"], overlay.title.text().strip(),
                                           overlay.mode.currentData())
            self.notice.setText(tr("Campaign template “{title}” saved.",
                                   title=overlay.title.text().strip()))
            self.changed.emit()

    def template_names(self, key: str | None, asset_id: int):
        """For another installation, the names of the elements the template makes; {} where
        nothing is made, None if the tester cancelled."""
        service = self.app.service
        if not key or not service.copy_needed(key, asset_id):
            return {}
        nodes = renamed(service.template(key))
        if not nodes:
            return {}
        overlay = TemplateCopyOverlay(nodes, self.app.db.asset(asset_id)["name"], self)
        return overlay.names() if overlay.exec() else None

    def follow_points(self, campaign_id: int, measurement_id: int | None) -> None:
        """Readings go on to the next open point of a template campaign."""
        campaign = self.app.service.campaign(campaign_id)
        if measurement_id is None or campaign is None or not is_template(campaign["plan_key"]):
            return
        row = self.app.db.one("SELECT step_id FROM measurements WHERE id=?", measurement_id)
        if row is None or row["step_id"] is None:
            return
        target = self.app.service.next_point(campaign_id, row["step_id"])
        if target is not None:
            self.place_targets[campaign_id] = target
            if campaign_id == self.campaign_id:
                self.structure.select(target)
                self._show_place(target)

    def learn_from(self, campaign_id: int) -> None:
        campaign = self.app.service.campaign(campaign_id)
        if self.app.service.template_mode(campaign["plan_key"]) != OPEN:
            return
        changes = self.app.service.template_changes(campaign_id)
        if not changes:
            return
        template = self.app.service.template(campaign["plan_key"])
        overlay = TemplateLearnOverlay(changes, template.title, self)
        if overlay.exec() and overlay.chosen():
            self.app.service.learn(campaign_id, overlay.chosen())
