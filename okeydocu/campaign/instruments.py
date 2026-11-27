# OkeyDocu - okeydocu/campaign/instruments.py
# The instruments booked into a campaign: each in, and out again while it has no readings.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Every instrument of a campaign counts the same. The first one is held in the campaign row
itself, slot 0, as a campaign with one instrument always was, so the seal of an ended campaign
reads as before; every further one is a row of campaign_instruments, its slot that row's id.
An instrument booked beside another never becomes the campaign's own: when the own one leaves,
the campaign is measured by hand with the others still beside it. An instrument takes back its
booking only while no reading of the campaign came from it: a reading names its instrument by
driver and serial number."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..l10n import tr
from ..model import DeviceIdentity
from .records import MANUAL, identity_from_json, identity_to_json


class InstrumentInUse(Exception):
    """The instrument measured in this campaign; its booking stays."""


@dataclass(frozen=True)
class Booked:
    slot: int  # 0: the campaign's own instrument; else the row of campaign_instruments
    driver: str
    identity: DeviceIdentity | None
    clock_offset_s: float
    booked_at: str

    @property
    def source(self) -> str:
        return f"device:{self.driver}"


def _now() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


class InstrumentsMixin:
    """Mixed into the campaign service, which has `db`, `campaign` and `measurements`."""

    def instruments(self, campaign_id: int) -> list[Booked]:
        campaign = self.campaign(campaign_id)
        found = []
        if campaign["driver"] != MANUAL:
            found.append(Booked(0, campaign["driver"], identity_from_json(campaign["device_json"]),
                                campaign["clock_offset_s"], campaign["started_at"]))
        for row in self.db.query("SELECT * FROM campaign_instruments WHERE campaign_id=?"
                                 " ORDER BY id", campaign_id):
            found.append(Booked(row["id"], row["driver"], identity_from_json(row["device_json"]),
                                row["clock_offset_s"], row["booked_at"]))
        return found

    def instrument(self, campaign_id: int, slot: int = 0) -> Booked | None:
        return next((booked for booked in self.instruments(campaign_id) if booked.slot == slot),
                    None)

    def book(self, campaign_id: int, driver: str, identity: DeviceIdentity | None = None,
             clock_offset_s: float = 0.0, beside: bool = False) -> int:
        """Books an instrument in and returns its slot. A campaign without one takes it as its
        own, unless it is to measure `beside` another."""
        device = identity_to_json(identity) if identity else "{}"
        with self.db.connection:
            if self.campaign(campaign_id)["driver"] == MANUAL and not beside:
                self.db.connection.execute(
                    "UPDATE campaigns SET driver=?, device_json=?, clock_offset_s=? WHERE id=?",
                    (driver, device, clock_offset_s, campaign_id))
                return 0
            return self.db.connection.execute(
                "INSERT INTO campaign_instruments (campaign_id, driver, device_json,"
                " clock_offset_s, booked_at) VALUES (?, ?, ?, ?, ?)",
                (campaign_id, driver, device, clock_offset_s, _now())).lastrowid

    def has_readings(self, campaign_id: int, slot: int) -> bool:
        booked = self.instrument(campaign_id, slot)
        if booked is None:
            return False
        serial = booked.identity.serial_no if booked.identity else ""
        return any(row["source"] == booked.source and (not serial or row["device_serial"] == serial)
                   for row in self.measurements(campaign_id))

    def release(self, campaign_id: int, slot: int) -> None:
        """Books an instrument out; without its own the campaign is one by hand."""
        if self.has_readings(campaign_id, slot):
            raise InstrumentInUse(tr("The instrument has measured in this campaign."))
        with self.db.connection:
            if slot:
                self.db.connection.execute(
                    "DELETE FROM campaign_instruments WHERE id=? AND campaign_id=?",
                    (slot, campaign_id))
                return
            self.db.connection.execute(
                "UPDATE campaigns SET driver=?, device_json='{}', clock_offset_s=0 WHERE id=?",
                (MANUAL, campaign_id))
            self.db.connection.execute("DELETE FROM clock_checks WHERE campaign_id=?",
                                       (campaign_id,))
