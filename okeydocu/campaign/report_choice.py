# OkeyDocu - okeydocu/campaign/report_choice.py
# The report template a campaign is given: its preview and its report are drawn with it.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Fable 5.2
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..l10n import tr
from ..store import CampaignClosed


class ReportChoiceMixin:
    """A campaign names its template; templates are kept by name, so renaming or deleting
    one leaves the campaign with the default template."""

    def report_template(self, campaign_id: int):
        """The template of the campaign, or the default one where it names none that exists;
        None while there is no template at all."""
        name = self.campaign(campaign_id)["report_template"]
        return next((row for row in self.db.templates() if row["name"] == name),
                    self.db.default_template())

    def set_report_template(self, campaign_id: int, name: str) -> None:
        if self.campaign(campaign_id)["status"] != "open":
            raise CampaignClosed(tr("The campaign is ended."))
        self.db.execute("UPDATE campaigns SET report_template=? WHERE id=?", name, campaign_id)
