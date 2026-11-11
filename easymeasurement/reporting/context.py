# EasyMeasurement - easymeasurement/reporting/context.py
# Collects everything a report may show into one plain data structure.
#
# Producer: thorsten.schnebeck@gmx.net
# Generator: Claude Opus 5.5
# SPDX-FileCopyrightText: (C) 2026 Thorsten Schnebeck <thorsten.schnebeck@gmx.net>
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

from ..campaign.photo_view import PhotoView
from ..campaign.repeat import REPEAT
from ..campaign.service import MANUAL, CampaignService
from ..model import (
    SIGHT_CHECK_FUNCTION,
    MeterMeasurement,
    Parameter,
    Verdict,
    conductor_of,
)
from ..devices import is_simulated, setting_words
from ..l10n import N_, in_language, tr
from ..vocabulary import function_label as vocabulary_label
from ..vocabulary import function_markup
from .attached import Attached, places, sort_attached
from .levels import asset_features, structure_levels
from .language import day, moment
from .logo import LogoError, decode_logo
from .measurement_words import said_settings
from .nodes import Markup

VERDICT_TEXT = {
    Verdict.PASSED: N_("passed"),
    Verdict.FAILED: N_("failed"),
    Verdict.NOT_EVALUATED: N_("not evaluated"),
}

@dataclass
class ReportMeasurement:
    data: MeterMeasurement
    local_time: datetime
    photos: list[Path] = field(default_factory=list)
    photo_notes: dict = field(default_factory=dict)  # path text: role, marks and view
    manual: bool = False  # typed in, not read from an instrument
    edited: bool = False  # something other than the reading was overwritten
    attached: Attached = field(default_factory=Attached)
    settings: list[tuple[str, str]] = field(default_factory=list)  # name and value, in words
    place_id: int | None = None  # the element of the installation it was taken at
    point: str = ""  # the step of the plan it was taken for


@dataclass
class ReportStep:
    title: str
    function: str
    status: str
    note: str
    measurements: list[ReportMeasurement] = field(default_factory=list)


def overall_verdict(steps: list[ReportStep]) -> str:
    """Summarise honestly: a skipped or empty step is not a pass."""
    verdicts = [m.data.verdict for step in steps for m in step.measurements]
    if Verdict.FAILED in verdicts:
        return tr("Failed")
    complete = bool(steps) and all(
        s.status == "done" and s.measurements for s in steps
    )
    if complete and all(v is Verdict.PASSED for v in verdicts):
        return tr("Passed")
    return tr("Not completely tested")


def _add_answers(steps: list[ReportStep], title: str, measured: list) -> None:
    """Answers in a row form one table under the name of their plan."""
    last = steps[-1] if steps else None
    if last and last.function == SIGHT_CHECK_FUNCTION and last.title == title:
        last.measurements.extend(measured)
    else:
        steps.append(ReportStep(in_language(title), SIGHT_CHECK_FUNCTION, "done", "", measured))


def _point_title(service: CampaignService, step, title: str) -> str:
    """A point left out names where and between which conductors it was to be taken."""
    where = service.place_path(step.asset_id) if step.asset_id is not None else ""
    conductor = conductor_of(Parameter(*item) for item in step.parameters)
    return " · ".join(part for part in (title, where, conductor) if part)


def build_context(service: CampaignService, campaign_id: int) -> dict:
    campaign = service.campaign(campaign_id)
    asset = service.db.asset(campaign["asset_id"])
    customer = service.db.customer(asset["customer_id"])
    identity = service.identity(campaign_id)
    words = setting_words(service.db)

    def load(row) -> ReportMeasurement:
        attached = sort_attached(service, service.attachments(campaign_id, measurement_id=row["id"]))
        notes = {
            str(service.photo_path(photo["campaign_id"], photo["file_name"])):
                (photo["role"], service.photo_marks(photo["id"]),
                 PhotoView.stored(photo["rotation"], photo["crop"]))
            for photo in service.photos_of(row["id"])
        }
        data = service.load_measurement(row)
        return ReportMeasurement(
            data,
            datetime.fromisoformat(row["local_time"]),
            service.photo_paths(row["id"]) + attached.images,
            notes,
            manual=row["source"] == MANUAL,
            # Who measured is registered, but it says nothing about the result.
            edited=any(c["field"] != "operator" for c in service.measurement_changes(row["id"])),
            attached=attached,
            settings=said_settings(words, data.parameters),
            place_id=row["asset_id"],
        )

    steps = []
    loose: dict[str, list[ReportMeasurement]] = {}
    repeat = campaign["plan_key"] == REPEAT
    for row in service.steps(campaign_id):
        plan_step = service.plan_step(row)
        measured = [load(m) for m in service.measurements(campaign_id, row["id"])]
        if plan_step.kind == "note":
            continue
        if plan_step.kind == "check" and row["status"] == "done":
            _add_answers(steps, plan_step.run or row["plan_title"], measured)
            continue
        # A repeat inspection reads like any other: its points are grouped by what was
        # measured; only one left out stands on its own, with its reason.
        if repeat and row["status"] == "done":
            loose.setdefault(plan_step.function, []).extend(measured)
            continue
        title = in_language(plan_step.title)
        if repeat:
            title = _point_title(service, plan_step, title)
        for measurement in measured:
            measurement.point = title
        steps.append(ReportStep(title, plan_step.function, row["status"], row["note"], measured))

    # Without a plan, measurements are simply grouped by what was measured.
    for row in service.open_measurements(campaign_id):
        loose.setdefault(row["function"], []).append(load(row))
    for function, measured in loose.items():
        title = Markup(function_markup(function))
        steps.append(ReportStep(title, function, "done", "", measured))

    measured = [m for step in steps for m in step.measurements]
    return {
        **company_context(service.db.company()),
        "customer": dict(customer),
        "asset": {**dict(asset), "kind_text": service.db.kind_labels().get(asset["kind"], ""),
                  "features": asset_features(service.db, asset)},
        "campaign": {
            "title": campaign["title"],
            "tester": campaign["tester"],
            "department": campaign["department"],
            "contact": campaign["contact"],
            "contact_phone": campaign["contact_phone"],
            "contact_email": campaign["contact_email"],
            "cost_center": campaign["cost_center"],
            "signature": _signature(service.db, campaign),
            "plan": campaign["plan_title"],
            "uuid": campaign["uuid"],
            "started": _date_text(campaign["started_at"]),
            "date": day(datetime.fromisoformat(campaign["started_at"])),
            "closed": _date_text(campaign["closed_at"]),
            "clock_offset_s": round(campaign["clock_offset_s"]),
            "clock_summary": clock_summary(
                campaign, service.clock_checks(campaign_id),
                [row["clock_offset_s"] for row in service.measurements(campaign_id)]),
            "seal": campaign["seal"],
            "simulated": is_simulated(campaign["driver"]),
            "draft": campaign["status"] == "open",
        },
        "device": {
            "manufacturer": identity.manufacturer,
            "model": identity.model,
            "serial_no": identity.serial_no,
            "firmware": identity.firmware,
            "calibrated_on": _day(identity.calibrated_on),
            "recalibration_due": _day(identity.recalibration_due),
            "overdue": identity.calibration_overdue(_reference_day(campaign)),
        },
        "steps": steps,
        "report": {"date": day(date.today())},
        "structure": structure_levels(service, campaign["asset_id"], measured),
        "places": places(service, campaign_id),
        "verdict": overall_verdict(steps),
        "verdict_tone": {tr("Passed"): "passed", tr("Failed"): "failed"}.get(
            overall_verdict(steps), ""),
    }


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
        moment = _date_text(check["checked_at"])
        if check["kind"] == "set":
            notes.append(tr("set on {moment} (deviation before {offset} s)",
                            moment=moment, offset=f"{check['offset_before_s']:+.0f}"))
        elif check["kind"] == "manual":
            notes.append(tr("offset set by hand to {offset} s on {moment}",
                            moment=moment, offset=f"{check['offset_s']:+.0f}"))
    offset = round(campaign["clock_offset_s"])
    if offset:
        notes.append(tr("offset {offset} s, the times below are corrected",
                        offset=f"{offset:+d}"))
    return "; ".join(notes)


def _signature(db, campaign) -> bytes | None:
    """A closed campaign keeps the signature of its day; a draft shows the inspector's own."""
    if campaign["signature"] or campaign["status"] != "open" or campaign["user_id"] is None:
        return campaign["signature"]
    user = db.user(campaign["user_id"])
    return user["signature"] if user else None


def _reference_day(campaign) -> date:
    return datetime.fromisoformat(campaign["started_at"]).date()


def _day(value: date | None) -> str:
    return day(value)


def _date_text(value: str | None) -> str:
    return moment(datetime.fromisoformat(value)) if value else "–"


def function_label(key: str) -> str:
    return vocabulary_label(key)
