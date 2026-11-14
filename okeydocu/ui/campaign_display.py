# OkeyDocu - okeydocu/ui/campaign_display.py
# What the campaign workspace shows: the chosen campaign, its controls and the status bar.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from html import escape

from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QWidget

from .. import APP_NAME
from ..campaign.service import NO_INSTRUMENT
from ..l10n import tr
from .campaign_items import SEPARATOR, count_text, order_line
from .dashboard_card import MAKE_REPORT, MENU, OPEN_REPORT, RESUME
from .report_signing import open_report


class CampaignDisplay:
    """Follows the campaign on screen and the session measuring, which may differ."""

    # What is on screen ---------------------------------------------------

    def _campaign(self):
        return self.app.service.campaign(self.campaign_id) if self.campaign_id else None

    def _driver(self, campaign):
        if campaign["status"] != "open" or campaign["driver"] in NO_INSTRUMENT:
            return None
        return self.app.devices.driver(campaign)

    def show_campaign(self, campaign_id: int) -> None:
        """Only shows. Whatever is measuring goes on measuring."""
        campaign = self.app.service.campaign(campaign_id)
        asset = self.app.db.asset(campaign["asset_id"])
        customer = self.app.db.customer(asset["customer_id"])
        self.campaign_id = campaign_id
        self.list.select(campaign_id)
        self.header.title.setText(campaign["title"])
        plan = campaign["plan_title"] or tr("Without plan")
        tester = escape(campaign["tester"]) or tr("Inspector missing")
        if campaign["status"] == "open":
            tester = f'<a href="tester">{tester}</a>'
        order = escape(order_line(campaign))
        parts = (escape(customer["name"]), escape(asset["name"]), order, tester, escape(plan))
        self.header.details.setText(SEPARATOR.join(part for part in parts if part))
        self.values.show_campaign(campaign_id)
        self.guided.show_campaign(campaign_id if self._has_plans(campaign) else None)
        self.structure.show_root(campaign["asset_id"], campaign_id, campaign["status"] == "open")
        self.structure.select(self.place_targets.get(campaign_id) or campaign["asset_id"])
        self._show_place(self.place_targets.get(campaign_id))
        self.reports.show_campaign(campaign_id)
        self._show_photos(campaign_id)
        self._show_plans(campaign)
        self.report_section.setVisible(campaign["status"] != "open")
        self.pages.setCurrentWidget(self.running)
        self.window().setWindowTitle(f"{campaign['title']} – {APP_NAME}")
        self._update()

    def show_home(self) -> None:
        """Whatever is measuring goes on; the start screen only takes the middle."""
        self.values.editor.apply()
        self.campaign_id = None
        self.list.select(None)
        self.pages.setCurrentWidget(self.home)
        self._refresh_home()
        self.window().setWindowTitle(APP_NAME)
        self._update()

    def _refresh_home(self) -> None:
        """Hidden, the start screen catches up when it is shown."""
        if self.pages.currentWidget() is self.home:
            self.home.live_id = self.live_id
            self.home.refresh()

    def _from_home(self, request: str, campaign_id: int) -> None:
        if request == MENU:
            self._campaign_menu(campaign_id, QCursor.pos())
            return
        if request == MAKE_REPORT:
            self.report_requested.emit(campaign_id)
            return
        if request == OPEN_REPORT:
            open_report(self.app, self.app.archive.reports(campaign_id)[0])
            return
        self.show_campaign(campaign_id)
        if request == RESUME:
            self._resume_from_list(campaign_id)

    def menu_actions(self) -> list:
        """What the context menu of a campaign offers: only what can be done with it now."""
        groups = [
            [self.resume_action, self.pause_action],
            [self.edit_action, self.tester_action, self.assign_action],
            [self.draft_action, self.finish_action, self.report_action],
            [self.next_order_action],
            [self.delete_action],
        ]
        result = []
        for group in groups:
            enabled = [action for action in group if action.isEnabled()]
            if enabled and result:
                result.append(None)
            result += enabled
        return result

    def campaign_menu(self, campaign_id: int) -> QMenu:
        """Shows the campaign first: the actions work on the one on screen."""
        self.show_campaign(campaign_id)
        menu = QMenu(self)
        for action in self.menu_actions():
            if action is None:
                menu.addSeparator()
            else:
                menu.addAction(action)
        return menu

    def _campaign_menu(self, campaign_id: int, position) -> None:
        self.campaign_menu(campaign_id).exec(position)

    def _show_loose(self, count: int) -> None:
        self.loose_section.setVisible(count > 0)
        self.loose_section.set_count(count)

    def _update(self) -> None:
        campaign = self._campaign()
        is_open = bool(campaign) and campaign["status"] == "open"
        instrument = is_open and campaign["driver"] not in NO_INSTRUMENT
        here = self.session is not None and self.live_id == self.campaign_id
        reachable = instrument and (self.session is None or here)
        guided = bool(campaign) and self.running_block() is not None
        manual = is_open and not instrument and not guided
        self.free.setVisible(manual or (here and not guided))
        if manual:
            self.free.show_campaign(campaign, None)
        elif here and not guided:
            self.free.show_campaign(campaign, self.session)
        self._show_link()
        self.resume_action.setEnabled(instrument and not here)
        self.pause_action.setEnabled(self.session is not None)
        empty = is_open and self.app.service.is_empty(campaign["id"])
        self.finish_action.setEnabled(is_open and not empty)
        self.draft_open = is_open
        self._proxies_changed()
        self.tester_action.setEnabled(is_open)
        self.edit_action.setEnabled(is_open)
        self.delete_action.setEnabled(bool(campaign))
        self.header.edit_button.setVisible(is_open)
        self.assign_action.setEnabled(is_open)
        self.report_action.setEnabled(bool(campaign) and not is_open)
        self.next_order_action.setEnabled(bool(campaign) and not is_open)
        self.photos_action.setEnabled(is_open)
        self.fetch_action.setEnabled(reachable)
        self.clock_action.setEnabled(reachable)
        self.offset_action.setEnabled(reachable)
        self.new_action.setEnabled(bool(self.app.db.assets()))
        self.list.new_button.setEnabled(self.new_action.isEnabled())
        self.header.resume_button.setVisible(instrument and not here)
        self.header.pause_button.setVisible(here)
        self.header.photos_button.setVisible(is_open)
        self.header.finish_button.setVisible(is_open and not empty)
        self.header.delete_button.setVisible(empty)
        # Once nothing is left to do, confirming is the next step and looks like it.
        ready = is_open and campaign["plan_key"] and not self.app.service.blockers(campaign["id"])
        self.header.finish_button.setStyleSheet("font-weight: bold;" if ready else "")
        self.header.draft_button.setVisible(is_open)
        self.header.report_button.setVisible(bool(campaign) and not is_open)
        self._show_checks(campaign)
        self._show_status(campaign)

    def _show_status(self, campaign) -> None:
        shown = self.live_id or self.campaign_id
        status = self.app.service.clock_status(shown) if shown else None
        self.clock.show_status(status)
        if campaign is None:
            self.summary.setText("")
            return
        count = self.app.service.measurement_counts().get(campaign["id"], 0)
        state = tr("open") if campaign["status"] == "open" else tr("completed")
        self.summary.setText(f"{count_text(count)}  ·  {state}")

    def current_work(self) -> QWidget | None:
        """What the operator is led by right now, if anything."""
        campaign = self._campaign()
        if campaign is None:
            return None
        if self.guided.isVisibleTo(self):
            return self.guided
        return self.free if self.free.isVisibleTo(self) else None
