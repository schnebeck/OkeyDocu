# EasyMeasurement - easymeasurement/ui/campaign_actions.py
# What can be done in the campaign workspace: start, measure, correct and close.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from ..campaign.service import read_instrument
from ..devices import Cancelled, DeviceError
from ..l10n import tr
from .campaign_dialog import CampaignDialog
from .campaign_tasks import CampaignTasks
from .common import run_busy, show_error
from .instrument_prepare import prepare_if_needed
from .live_session import LiveSession
from .measurement_detail import pick_images


class CampaignActions(CampaignTasks):
    """Starting a campaign, the live session it measures in, and all that follows."""

    # Starting ------------------------------------------------------------

    def new_campaign(self, asset_id: int = 0, title: str = "", follows: int = 0) -> None:
        """`asset_id` and `title` fill the dialog in; `follows` marks a follow-up inspection."""
        dialog = CampaignDialog(self.app, self, plans=self.guided.plans)
        if asset_id:
            dialog.asset.setCurrentIndex(max(dialog.asset.findData(asset_id), 0))
        if title:
            dialog.title.setText(title)
        newest = self.app.db.one("SELECT max(id) AS id FROM campaigns")["id"] or 0
        if not dialog.exec():
            return
        asset, plan = dialog.asset.currentData(), dialog.plan.currentData()
        title, instrument = dialog.title.text().strip(), dialog.source.currentData()
        tester, user = dialog.tester.current_name(), dialog.tester.current_id()
        self._end_session()  # the instrument is about to be asked for by the new campaign
        if plan is not None:
            self.guided.start_campaign(
                asset, plan, title, tester, instrument.key, instrument.port, user
            )
        elif instrument is None:
            self.enter(self.app.service.create(asset, title, tester, user_id=user))
        else:
            self._start_free(asset, title, tester, user, instrument)
        created = self.app.db.one("SELECT max(id) AS id FROM campaigns")["id"] or 0
        if follows and created > newest:
            self.app.service.mark_follow_up(created, follows)
        if dialog.repeat.isChecked() and dialog.previous is not None and created > newest:
            self.app.service.make_repeat(created, dialog.previous["id"])
            self.show_campaign(created)
        self.list.refresh()
        self._update()
        self.changed.emit()

    def _start_free(self, asset: int, title: str, tester: str, user, instrument) -> None:
        driver = self.app.devices.new_driver(instrument.key, instrument.port)

        def connect():
            with driver:
                return read_instrument(driver)

        try:
            text = tr("Connecting to the instrument and setting the clock …")
            start = run_busy(self, text, connect, driver.abort)
        except Cancelled:
            return
        except DeviceError as err:
            show_error(self, str(err))
            return
        prepare_if_needed(self.app, instrument.key, instrument.port, start.identity,
                          driver.capabilities, self)
        campaign = self.app.service.open_with(
            asset, None, title, tester, instrument.key, start, user
        )
        self.app.devices.attach(campaign, driver, instrument.port)
        self.instrument.unbroken.add(campaign)
        self.enter(campaign)

    # Measuring -----------------------------------------------------------

    def enter(self, campaign_id: int) -> None:
        """Shows the campaign and gives it the instrument, if it uses one."""
        driver = self._driver(self.app.service.campaign(campaign_id))
        if self.live_id != campaign_id:
            self._end_session()
        starting = driver is not None and self.session is None
        if starting:
            self.session = LiveSession(driver, campaign_id, self)
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

    def _received(self, campaign_id: int, reading) -> None:
        """Stored first. Everything else can wait, this value exists nowhere else."""
        self.app.service.receive(campaign_id, reading, self.place_target(campaign_id))
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

    def _selector_read(self, position) -> None:
        if self.live_id == self.campaign_id:
            self.guided.show_selector(position)
            self.free.instruction.show_selector(position)

    def _end_session(self) -> None:
        session, self.session = self.session, None
        if session is not None:
            self.instrument.unbroken.discard(session.campaign_id)
        self.instrument.session = None
        self.live_id = self.list.live_id = None
        self.link_state = None
        self.link.show_link(None)
        if session is not None:
            run_busy(self, tr("Disconnecting from the instrument …"), session.stop)
            session.deleteLater()
            warning, session.driver.stop_warning = session.driver.stop_warning, ""
            if warning:
                show_error(self, warning)

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
