# OkeyDocu - okeydocu/ui/campaign_actions.py
# What can be done in the campaign workspace: start, measure, correct and close.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from shiboken6 import isValid

from ..campaign.service import MANUAL
from ..campaign.setting_check import SettingCheck
from ..l10n import tr
from .campaign_dialog import CampaignDialog
from .campaign_tasks import CampaignTasks
from ..devices import driver_info
from .common import run_busy
from .instrument_start import reach_instrument
from .live_session import LiveSession
from .measurement_detail import pick_images
from .setting_warning import SettingsWarning


class CampaignActions(CampaignTasks):
    """Starting a campaign, the live session it measures in, and all that follows."""

    settings_warning = None  # the card about the last reading's settings, while it is open

    # Starting ------------------------------------------------------------

    def new_campaign(self, asset_id: int = 0, title: str = "", follows: int = 0,
                     repeat_of: int = 0) -> None:
        """`asset_id` and `title` fill the dialog in; `follows` marks a follow-up inspection;
        `repeat_of` is the order the new one repeats, on its installation."""
        dialog = CampaignDialog(self.app, self, plans=self.guided.plans, repeat_of=repeat_of)
        if repeat_of:
            asset_id = self.app.service.campaign(repeat_of)["asset_id"]
        if asset_id:
            dialog.asset.setCurrentIndex(max(dialog.asset.findData(asset_id), 0))
        if title:
            dialog.title.setText(title)
        if not dialog.exec():
            return
        asset, plan = dialog.asset.currentData(), dialog.plan.currentData()
        title, instrument = dialog.title.text().strip(), dialog.source.currentData()
        tester, user = dialog.tester.current_name(), dialog.tester.current_id()
        template = dialog.template.currentData()
        names = self.template_names(template, asset)
        if names is None:
            return
        self._end_session()  # the instrument is about to be asked for by the new campaign
        created = self.app.service.create(
            asset, title, tester, plan, instrument.key if instrument else MANUAL, user_id=user,
            awaiting=instrument is not None,
        )
        if instrument is not None:
            self.app.devices.ports[created] = instrument.port
        self.app.service.set_contact(created, *dialog.order.contact_values())
        self.app.service.set_order(created, *dialog.order.order_values())
        self.app.service.set_report_template(created, dialog.report_template.currentText())
        if follows:
            self.app.service.mark_follow_up(created, follows)
        if dialog.repeat.isChecked() and dialog.previous is not None:
            self.app.service.make_repeat(created, dialog.previous["id"])
        if template:
            self.app.service.use_template(created, template, names)
        if plan is not None:
            self.guided.opened(created)
        else:
            self.enter(created)
        self.list.refresh()
        self._update()
        self.changed.emit()

    # Measuring -----------------------------------------------------------

    def enter(self, campaign_id: int) -> None:
        """Shows the campaign and gives it the instrument, if it uses one. An instrument not
        read yet is read first; if it does not answer, the campaign is only shown."""
        if self.app.service.awaits_instrument(campaign_id):
            self._end_session()
            if not reach_instrument(self.app, self, campaign_id):
                self.list.refresh()
                self.show_campaign(campaign_id)
                return
            self.instrument.unbroken.add(campaign_id)
        driver = self._driver(self.app.service.campaign(campaign_id))
        if self.live_id != campaign_id:
            self._end_session()
        starting = driver is not None and self.session is None
        if starting:
            name = tr(driver_info(self.app.service.campaign(campaign_id)["driver"]).label)
            self.session = LiveSession(driver, campaign_id, self, name)
            self.session.reading.connect(self._received)
            self.session.link.connect(self._link_changed)
            self.session.selector.connect(self._selector_read)
            self.instrument.session = self.session
            self.live_id = self.list.live_id = campaign_id
        self.list.refresh()
        self.show_campaign(campaign_id)
        if starting:
            self.session.start()

    def resume(self) -> None:
        if self.campaign_id is not None:
            self.enter(self.campaign_id)

    def _resume_from_list(self, campaign_id: int) -> None:
        if self._driver(self.app.service.campaign(campaign_id)) is not None:
            self.enter(campaign_id)

    def pause(self) -> None:
        self._end_session()
        self.list.refresh()
        if self.campaign_id is not None:
            self.show_campaign(self.campaign_id)

    def _link_changed(self, kind: str, text: str) -> None:
        if self.session is not None:  # a report from a session just ended says nothing
            self.link_state = (kind, text)
            self._show_link()

    def _show_link(self) -> None:
        if self.link_state is None:
            self.link.show_link(None)
            return
        kind, text = self.link_state
        if self.live_id == self.campaign_id:
            self.free.show_link(kind)
        else:
            title = self.app.service.campaign(self.live_id)["title"]
            text = tr("{state}, measuring for “{title}”", state=text, title=title)
        self.link.show_link(kind, text)

    def _received(self, campaign_id: int, reading, slot: int = 0) -> None:
        """Stored first. Everything else can wait, this value exists nowhere else."""
        measurement_id = self.app.service.receive(campaign_id, reading,
                                                  self.place_target(campaign_id), slot=slot)
        self.guide_reading(campaign_id, reading)
        self.follow_points(campaign_id, measurement_id)
        self.list.update_campaign(campaign_id)
        self._refresh_home()
        if campaign_id == self.campaign_id:
            self.guided.show_received(reading)
            self.free.instruction.show_function(reading.measurement.function)
            self.values.refresh()
            self.values.show_newest()
            self._refresh_structure()
            self._refresh_photos()
        self._update()
        self.changed.emit()
        if measurement_id is not None:
            self._warn_settings(measurement_id)

    def _warn_settings(self, measurement_id: int) -> None:
        """At once, while the tester can still set the instrument right; a newer warning
        takes the place of one still open."""
        row = self.app.db.one("SELECT * FROM measurements WHERE id=?", measurement_id)
        found = SettingCheck(self.app.db).of_row(row)
        if not found:
            return
        previous = self.settings_warning
        if previous is not None and isValid(previous) and previous.isVisible():
            previous.accept()
        self.settings_warning = SettingsWarning(found, self)
        self.settings_warning.open()

    def _selector_read(self, position) -> None:
        if self.live_id == self.campaign_id:
            self.guided.show_selector(position)
            self.free.instruction.show_selector(position)
            self.guide_selector(position)

    def _end_session(self) -> None:
        session, self.session = self.session, None
        self.close_guide()
        if session is not None:
            self.instrument.unbroken.discard(session.campaign_id)
        self.instrument.session = None
        self.live_id = self.list.live_id = None
        self.link_state = None
        self.link.show_link(None)
        if session is not None:
            run_busy(self, tr("Disconnecting from the instrument …"), session.stop)
            session.deleteLater()

    def import_photos(self) -> None:
        files = pick_images(self)
        if not files:
            return
        result = self.app.service.import_photos(self.campaign_id, files)
        self.notice.setText(tr("{matched} photos assigned, {open} open, {duplicates} already"
                               " there.", matched=result["matched"], open=result["open"],
                               duplicates=result["duplicates"]))
        self.guided.reload()
        self._data_changed()
        self.warm_proxies(self.campaign_id)
        if result["matched"] or result["open"]:
            self.timeline_action.setChecked(True)  # the next step is checking where they went

    def shut_down(self) -> None:
        self._end_session()
