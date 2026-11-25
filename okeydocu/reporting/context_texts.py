# OkeyDocu - okeydocu/reporting/context_texts.py
# Small pieces of a report's data: the firm, the instrument clock, the signature, dates.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from datetime import date, datetime

from ..l10n import signed_seconds, tr
from .language import day, moment
from .logo import LogoError, decode_logo


def company_context(company: dict[str, str]) -> dict:
    """The firm's texts for placeholders; its logo apart, as image data for the letterhead."""
    logo = company.get("logo", "")
    try:
        data = decode_logo(logo) if logo else None
    except LogoError:
        data = None
    return {"company": {k: v for k, v in company.items() if k != "logo"}, "company_logo": data}


def clock_summary(campaign, checks, offsets) -> str:
    """Say which offset the times rest on, including any change along the way.

    Empty while no time was corrected: a clock set before measuring leaves nothing to tell.
    """
    corrected = any(abs(offset or 0) >= 1 for offset in offsets)
    if not (corrected or round(campaign["clock_offset_s"])
            or any(check["kind"] == "manual" for check in checks)):
        return ""
    notes = []
    for check in checks:
        moment = date_text(check["checked_at"])
        if check["kind"] == "set":
            notes.append(tr("set on {moment} (deviation before {offset} s)",
                            moment=moment, offset=signed_seconds(check['offset_before_s'])))
        elif check["kind"] == "manual":
            notes.append(tr("offset set by hand to {offset} s on {moment}",
                            moment=moment, offset=signed_seconds(check['offset_s'])))
    offset = round(campaign["clock_offset_s"])
    if offset:
        notes.append(tr("offset {offset} s, the times below are corrected",
                        offset=signed_seconds(offset)))
    return "; ".join(notes)


def campaign_signature(db, campaign) -> bytes | None:
    """A closed campaign keeps the signature of its day; a draft shows the inspector's own."""
    if campaign["signature"] or campaign["status"] != "open" or campaign["user_id"] is None:
        return campaign["signature"]
    user = db.user(campaign["user_id"])
    return user["signature"] if user else None


def signing_day(campaign) -> date:
    """The day the report is signed: the campaign was ended and sealed with the inspector's
    signature. A draft is not signed yet and shows today."""
    closed = campaign["closed_at"]
    return datetime.fromisoformat(closed).date() if closed else date.today()


def days_text(first: date, last: date) -> str:
    """The day of a test, or its first and its last where it took several."""
    return day(first) if first == last else f"{day(first)} \u2013 {day(last)}"


def date_text(value: str | None) -> str:
    return moment(datetime.fromisoformat(value)) if value else "–"
