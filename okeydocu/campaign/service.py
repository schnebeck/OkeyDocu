# OkeyDocu - okeydocu/campaign/service.py
# Campaigns and their data: measurements and values from any source.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from ..devices.base import MeterDriver
from ..model import DeviceIdentity
from ..store import Database
from .clock import (
    CLOCK_SET_ACCURACY_S,
    CLOCK_TOLERANCE_S,
    ClockMixin,
    ClockState,
    ClockStatus,
    InstrumentStart,
    clock_needs_setting,
    measure_clock_offset,
    read_instrument,
    set_instrument_clock,
)
from .attachments import AttachmentMixin
from .closing import ClosingMixin
from .editing import EditingMixin
from .filing import FilingMixin
from .due import DueMixin
from .overview import CampaignSummary, OverviewMixin
from .structure import StructureError, StructureMixin
from .photo_marks import PhotoMarkMixin
from .carry_over import CarryOverMixin
from .instrument_history import InstrumentHistoryMixin
from .photo_proxies import ProxyMixin
from .photo_values import PhotoMixin
from .plan_blocks import PlanBlockMixin
from .plan_steps import PlanStepMixin
from .plan import Plan
from .repeat import RepeatMixin
from .repeat_checks import RepeatCheckMixin
from .runs import RunMixin
from .records import (
    EDITABLE_FIELDS,
    EDITABLE_VALUE_FIELDS,
    IMPORTED,
    LOCATION_SEPARATOR,
    MANUAL,
    NO_INSTRUMENT,
    TEXT_FIELDS,
    ReadingMixin,
    _iso,
    full_name,
    identity_from_json,
    identity_to_json,
)
from .seal import KeyStore

__all__ = [
    "CLOCK_SET_ACCURACY_S",
    "CLOCK_TOLERANCE_S",
    "EDITABLE_FIELDS",
    "EDITABLE_VALUE_FIELDS",
    "IMPORTED",
    "LOCATION_SEPARATOR",
    "MANUAL",
    "NO_INSTRUMENT",
    "TEXT_FIELDS",
    "CampaignService",
    "CampaignSummary",
    "StructureError",
    "ClockState",
    "ClockStatus",
    "InstrumentStart",
    "clock_needs_setting",
    "full_name",
    "identity_from_json",
    "identity_to_json",
    "measure_clock_offset",
    "read_instrument",
    "set_instrument_clock",
]


class CampaignService(
    ReadingMixin, ClockMixin, FilingMixin, EditingMixin, PhotoMixin, AttachmentMixin, PlanStepMixin,
    PlanBlockMixin, ClosingMixin, OverviewMixin, StructureMixin, DueMixin, RunMixin, RepeatMixin,
    RepeatCheckMixin, PhotoMarkMixin, ProxyMixin, CarryOverMixin, InstrumentHistoryMixin,
):
    def __init__(self, db: Database, archive_root: Path, key_store: KeyStore | None = None):
        self.db = db
        self.archive_root = archive_root
        self.key_store = key_store
        self._key: bytes | None = None

    def seal_key(self) -> bytes | None:
        """Reading KWallet can take a while, so call this off the GUI thread first."""
        if self._key is None and self.key_store is not None:
            self._key = self.key_store.key()
        return self._key

    # Creating ------------------------------------------------------------

    def create(
        self, asset_id: int, title: str, tester: str, plan: Plan | None = None,
        driver_key: str = MANUAL, identity: DeviceIdentity | None = None,
        clock_offset_s: float = 0.0, offset_before_s: float | None = None,
        stored_since: datetime | None = None, user_id: int | None = None,
    ) -> int:
        """Open a campaign. No instrument and no plan are needed.

        `tester` is the name as the record states it: it stays, whatever later
        happens to the person's entry, which `user_id` points to.
        """
        with self.db.connection:
            campaign_id = self.db.connection.execute(
                "INSERT INTO campaigns (uuid, asset_id, plan_key, plan_title, title, tester, driver,"
                " device_json, clock_offset_s, baseline_json, stored_since, started_at, user_id)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    str(uuid.uuid4()), asset_id, plan.key if plan else "",
                    plan.label if plan else "", title, tester, driver_key,
                    identity_to_json(identity) if identity else "{}", clock_offset_s,
                    "[]", _iso(stored_since) if stored_since else None,
                    _iso(datetime.now()), user_id,
                ),
            ).lastrowid
            if driver_key != MANUAL:
                self.db.connection.execute(
                    "INSERT INTO clock_checks (campaign_id, checked_at, kind, offset_s,"
                    " offset_before_s) VALUES (?, ?, ?, ?, ?)",
                    (
                        campaign_id, _iso(datetime.now()),
                        "measured" if offset_before_s is None else "set",
                        clock_offset_s, offset_before_s,
                    ),
                )
            if plan:
                self._insert_steps(self.db.connection, campaign_id, plan)
        previous = self.last_contact(asset_id, campaign_id)
        if previous:  # the same person is the likeliest one to ask again
            self.set_contact(campaign_id, *previous)
        return campaign_id

    def start(
        self, asset_id: int, plan: Plan | None, title: str, tester: str, driver_key: str,
        driver: MeterDriver,
    ) -> int:
        """Open a campaign with an instrument attached."""
        return self.open_with(asset_id, plan, title, tester, driver_key, read_instrument(driver))

    def open_with(
        self, asset_id: int, plan: Plan | None, title: str, tester: str, driver_key: str,
        start: InstrumentStart, user_id: int | None = None,
    ) -> int:
        return self.create(
            asset_id, title, tester, plan, driver_key, start.identity, start.offset_s,
            offset_before_s=start.offset_before_s, stored_since=start.stored_since,
            user_id=user_id,
        )
